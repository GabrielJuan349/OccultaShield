from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
from typing import AsyncGenerator

from services.progress_manager import progress_manager, ProgressManager
from core.events import ProcessingPhase
from auth import get_current_user  # Tu sistema de auth

router = APIRouter(prefix="/api/v1/process", tags=["Processing"])


async def event_generator(
    video_id: str,
    request: Request
) -> AsyncGenerator[str, None]:
    """
    Generador de eventos SSE para un video.
    Se mantiene vivo mientras el cliente está conectado.
    """
    queue = await progress_manager.subscribe(video_id)
    
    try:
        # Enviar estado inicial
        state = await progress_manager.get_state(video_id)
        if state:
            yield f"event: initial_state\ndata: {state.to_dict()}\n\n"
        
        # Heartbeat cada 15 segundos para mantener conexión
        heartbeat_interval = 15
        last_heartbeat = asyncio.get_event_loop().time()
        
        while True:
            # Verificar si cliente desconectó
            if await request.is_disconnected():
                break
            
            try:
                # Esperar evento con timeout para heartbeat
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=heartbeat_interval
                )
                
                # Enviar evento
                yield event.to_sse()
                
                # Si es evento de completado o error, terminar
                if event.event_type.value in ["complete", "error"]:
                    break
                    
            except asyncio.TimeoutError:
                # Enviar heartbeat
                current_time = asyncio.get_event_loop().time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    yield f"event: heartbeat\ndata: {{}}\n\n"
                    last_heartbeat = current_time
                    
    finally:
        await progress_manager.unsubscribe(video_id, queue)


@router.get("/{video_id}/progress")
async def stream_progress(
    video_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    SSE endpoint para recibir progreso en tiempo real.
    
    Eventos emitidos:
    - initial_state: Estado inicial al conectar
    - phase_change: Cambio de fase de procesamiento
    - progress: Actualización de porcentaje
    - detection: Nueva detección encontrada
    - verification: Progreso de verificación
    - complete: Procesamiento terminado
    - error: Error ocurrido
    - heartbeat: Keep-alive cada 15s
    """
    # Verificar que el video existe y pertenece al usuario
    state = await progress_manager.get_state(video_id)
    if not state:
        raise HTTPException(404, f"No active processing for video {video_id}")
    
    return EventSourceResponse(
        event_generator(video_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Para nginx
        }
    )


@router.get("/{video_id}/status")
async def get_status(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene el estado actual sin SSE (polling fallback).
    """
    state = await progress_manager.get_state(video_id)
    if not state:
        raise HTTPException(404, f"No active processing for video {video_id}")
    
    return state.to_dict()


@router.post("/{video_id}/cancel")
async def cancel_processing(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancela el procesamiento de un video.
    """
    state = await progress_manager.get_state(video_id)
    if not state:
        raise HTTPException(404, f"No active processing for video {video_id}")
    
    await progress_manager.error(
        video_id=video_id,
        code="CANCELLED",
        message="Processing cancelled by user",
        recoverable=True
    )
    
    return {"status": "cancelled", "video_id": video_id}