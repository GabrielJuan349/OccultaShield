import asyncio
from typing import Dict, Optional, AsyncGenerator, Callable, Any
from datetime import datetime
from collections import defaultdict

from core.events import (
    ProcessingPhase, 
    ProgressEvent, 
    PhaseChangeEvent,
    DetectionEvent,
    VerificationEvent,
    CompleteEvent,
    ErrorEvent
)

class VideoProgressState:
    """Estado de progreso de un video individual."""
    
    def __init__(self, video_id: str):
        self.video_id = video_id
        self.phase = ProcessingPhase.IDLE
        self.progress = 0
        self.current_item = 0
        self.total_items = 0
        self.message = ""
        self.started_at: Optional[datetime] = None
        self.detections: Dict[str, int] = defaultdict(int)  # type -> count
        self.errors: list = []
        
    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "phase": self.phase.value,
            "progress": self.progress,
            "current": self.current_item,
            "total": self.total_items,
            "message": self.message,
            "detections": dict(self.detections),
            "elapsed_seconds": (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
        }


class ProgressManager:
    """
    Gestor centralizado de progreso para múltiples videos.
    Implementa patrón pub/sub para SSE.
    """
    
    _instance: Optional["ProgressManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Estado por video
        self._states: Dict[str, VideoProgressState] = {}
        
        # Subscribers por video (para SSE)
        self._subscribers: Dict[str, list[asyncio.Queue]] = defaultdict(list)
        
        # Lock para thread safety
        self._lock = asyncio.Lock()
        
        self._initialized = True
    
    async def register_video(self, video_id: str) -> VideoProgressState:
        """Registra un nuevo video para tracking."""
        async with self._lock:
            state = VideoProgressState(video_id)
            state.started_at = datetime.now()
            self._states[video_id] = state
            print(f"📊 [PROGRESS] Registered video: {video_id}")
            return state
    
    async def get_state(self, video_id: str) -> Optional[VideoProgressState]:
        """Obtiene estado actual de un video."""
        return self._states.get(video_id)
    
    async def subscribe(self, video_id: str) -> asyncio.Queue:
        """
        Suscribe un cliente SSE a eventos de un video.
        Retorna una queue donde se enviarán los eventos.
        """
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers[video_id].append(queue)
        return queue
    
    async def unsubscribe(self, video_id: str, queue: asyncio.Queue):
        """Desuscribe un cliente SSE."""
        async with self._lock:
            if video_id in self._subscribers:
                try:
                    self._subscribers[video_id].remove(queue)
                except ValueError:
                    pass
    
    async def _broadcast(self, video_id: str, event: Any):
        """Envía evento a todos los subscribers de un video."""
        if video_id not in self._subscribers:
            print(f"📡 [BROADCAST] No subscribers for {video_id}")
            return
        
        num_subs = len(self._subscribers[video_id])
        print(f"📡 [BROADCAST] {video_id}: sending {event.event_type.value} to {num_subs} subscriber(s)")
        
        dead_queues = []
        for queue in self._subscribers[video_id]:
            try:
                await asyncio.wait_for(
                    queue.put(event),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                dead_queues.append(queue)
            except Exception:
                dead_queues.append(queue)
        
        # Limpiar queues muertas
        for queue in dead_queues:
            try:
                self._subscribers[video_id].remove(queue)
            except ValueError:
                pass
    
    # ===== MÉTODOS PARA EMITIR EVENTOS =====
    
    async def change_phase(
        self, 
        video_id: str, 
        phase: ProcessingPhase,
        message: str,
        estimated_time: Optional[int] = None
    ):
        """Cambia la fase de procesamiento."""
        state = self._states.get(video_id)
        if not state:
            return
        
        previous_phase = state.phase
        state.phase = phase
        state.message = message
        state.progress = 0  # Reset progress on phase change
        
        event = PhaseChangeEvent(
            phase=phase,
            previous_phase=previous_phase,
            message=message,
            estimated_time_seconds=estimated_time
        )
        
        print(f"🔄 [PHASE CHANGE] {video_id}: {previous_phase.value} -> {phase.value}")
        print(f"   Message: {message}")
        await self._broadcast(video_id, event)
    
    async def update_progress(
        self,
        video_id: str,
        progress: int,
        current: Optional[int] = None,
        total: Optional[int] = None,
        message: Optional[str] = None
    ):
        """Actualiza el progreso actual."""
        state = self._states.get(video_id)
        if not state:
            return
        
        state.progress = min(100, max(0, progress))
        if current is not None:
            state.current_item = current
        if total is not None:
            state.total_items = total
        if message:
            state.message = message
        
        event = ProgressEvent(
            phase=state.phase,
            progress=state.progress,
            current=state.current_item,
            total=state.total_items,
            message=state.message
        )
        
        await self._broadcast(video_id, event)
    
    async def report_detection(
        self,
        video_id: str,
        detection_type: str,
        frame_number: int,
        confidence: float
    ):
        """Reporta una nueva detección."""
        state = self._states.get(video_id)
        if not state:
            return
        
        state.detections[detection_type] += 1
        count = state.detections[detection_type]
        
        event = DetectionEvent(
            detection_type=detection_type,
            count=count,
            frame_number=frame_number,
            confidence=confidence,
            message=f"Detected {detection_type} #{count} at frame {frame_number}"
        )
        
        await self._broadcast(video_id, event)
    
    async def report_verification(
        self,
        video_id: str,
        vulnerability_id: str,
        status: str,
        agents_completed: int,
        total_agents: int
    ):
        """Reporta progreso de verificación multi-agente."""
        event = VerificationEvent(
            vulnerability_id=vulnerability_id,
            status=status,
            agents_completed=agents_completed,
            total_agents=total_agents,
            message=f"Verifying: {agents_completed}/{total_agents} agents complete"
        )
        
        await self._broadcast(video_id, event)
    
    async def complete(
        self,
        video_id: str,
        total_vulnerabilities: int,
        total_violations: int,
        redirect_url: Optional[str] = None
    ):
        """Marca el procesamiento como completado."""
        state = self._states.get(video_id)
        if not state:
            return
        
        state.phase = ProcessingPhase.COMPLETED
        state.progress = 100
        
        elapsed = (datetime.now() - state.started_at).total_seconds() if state.started_at else 0
        
        # Default redirect to download page
        final_redirect = redirect_url or f"/download/{video_id}"
        
        event = CompleteEvent(
            video_id=video_id,
            total_vulnerabilities=total_vulnerabilities,
            total_violations=total_violations,
            processing_time_seconds=elapsed,
            redirect_url=final_redirect,
            message=f"Processing complete! Found {total_violations} violations."
        )
        
        await self._broadcast(video_id, event)
    
    async def error(
        self,
        video_id: str,
        code: str,
        message: str,
        details: Optional[str] = None,
        recoverable: bool = False
    ):
        """Reporta un error."""
        state = self._states.get(video_id)
        if state:
            state.phase = ProcessingPhase.ERROR
            state.errors.append({"code": code, "message": message})
        
        event = ErrorEvent(
            code=code,
            message=message,
            details=details,
            recoverable=recoverable
        )
        
        await self._broadcast(video_id, event)
    
    async def cleanup(self, video_id: str):
        """Limpia estado y subscribers de un video."""
        async with self._lock:
            if video_id in self._states:
                del self._states[video_id]
            if video_id in self._subscribers:
                del self._subscribers[video_id]


# Singleton global
progress_manager = ProgressManager()