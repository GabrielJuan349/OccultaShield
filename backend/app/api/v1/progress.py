from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import json
import logging
from typing import AsyncGenerator

from services.progress_manager import progress_manager, ProgressManager
from core.events import ProcessingPhase
from core.dependencies import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Processing"])


async def event_generator(
    video_id: str,
    request: Request
) -> AsyncGenerator[dict, None]:
    """
    Generador de eventos SSE para un video.
    Se mantiene vivo mientras el cliente está conectado.

    IMPORTANTE: sse_starlette espera diccionarios con keys:
    - event: nombre del evento
    - data: datos del evento (string JSON)
    - id: (opcional) ID del evento
    - retry: (opcional) tiempo de retry en ms
    """
    print(f"🎬 [SSE] event_generator started for video: {video_id}")
    queue = await progress_manager.subscribe(video_id)
    print(f"📡 [SSE] Subscribed to queue for video: {video_id}")

    try:
        # Enviar estado inicial
        state = await progress_manager.get_state(video_id)
        print(f"📊 [SSE] Got state for {video_id}: {state is not None}")

        if state:
            state_dict = state.to_dict()
            print(f"📤 [SSE] Sending initial_state to client for {video_id}")
            print(f"   State data: phase={state_dict.get('phase')}, progress={state_dict.get('progress')}")
            yield {"event": "initial_state", "data": json.dumps(state_dict)}
        else:
            # Si no hay estado, enviar estado idle por defecto
            print(f"⚠️ [SSE] No state found for {video_id}, sending default idle state")
            default_state = {
                "video_id": video_id,
                "phase": "idle",
                "progress": 0,
                "current": 0,
                "total": 0,
                "message": "Waiting for processing to start...",
                "detections": {},
                "elapsed_seconds": 0
            }
            yield {"event": "initial_state", "data": json.dumps(default_state)}

        # Heartbeat cada 15 segundos para mantener conexión
        heartbeat_interval = 15
        last_heartbeat = asyncio.get_event_loop().time()

        while True:
            # Verificar si cliente desconectó
            if await request.is_disconnected():
                print(f"🔌 [SSE] Client disconnected for {video_id}")
                break

            try:
                # Esperar evento con timeout para heartbeat
                event = await asyncio.wait_for(
                    queue.get(),
                    timeout=heartbeat_interval
                )

                # Enviar evento usando formato de diccionario
                event_type = event.event_type.value
                print(f"📤 [SSE] Sending {event_type} event to client")

                try:
                    event_data = event.model_dump(mode='json')
                    yield {"event": event_type, "data": json.dumps(event_data)}
                except Exception as serialize_error:
                    logger.error(f"SSE serialization error: {serialize_error}")
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "message": f"Error sending progress update: {str(serialize_error)}"
                        })
                    }

                # Si es evento de completado o error, terminar
                if event_type in ["complete", "error"]:
                    print(f"📤 [SSE] Terminal event ({event_type}) - closing connection")
                    break

            except asyncio.TimeoutError:
                # Enviar heartbeat
                current_time = asyncio.get_event_loop().time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    print(f"💓 [SSE] Sending heartbeat for {video_id}")
                    yield {"event": "heartbeat", "data": "{}"}
                    last_heartbeat = current_time
                    
    finally:
        await progress_manager.unsubscribe(video_id, queue)


@router.get("/{video_id}/progress")
async def stream_progress(
    video_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    SSE endpoint para recibir progreso en tiempo real.

    Cuando se conecta un cliente, automáticamente inicia el procesamiento
    si el video está en estado 'uploaded' (esperando procesamiento).

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
    from services.video_processor import video_processor
    from datetime import datetime

    # Debug: Ver qué videos están registrados
    print(f"\n🔌 [SSE CONNECTION REQUEST]")
    print(f"   video_id requested: {video_id}")
    print(f"   user: {current_user.get('id', 'unknown')}")
    print(f"   registered videos in memory: {list(progress_manager._states.keys())}")

    # 1️⃣ PRIMERO: Verificar que el video existe en DB y pertenece al usuario
    db_video_id = f"video:`{video_id}`"
    print(f"   🔍 Buscando video en DB: {db_video_id}")

    try:
        result = await db.select(db_video_id)
        video = result if not isinstance(result, list) else (result[0] if result else None)
    except Exception as e:
        print(f"   ❌ Error consultando DB: {e}")
        raise HTTPException(500, f"Database error: {e}")

    if not video:
        print(f"   ❌ Video no encontrado en DB")
        raise HTTPException(404, f"Video {video_id} not found")

    # Verificar ownership
    video_user_id = str(video.get("user_id")).replace("⟨", "").replace("⟩", "")
    current_user_id = str(current_user["id"]).replace("⟨", "").replace("⟩", "")

    if video_user_id != current_user_id:
        print(f"   ❌ Video no pertenece al usuario: {video_user_id} != {current_user_id}")
        raise HTTPException(403, "Not authorized to access this video")

    print(f"   ✅ Video encontrado en DB, status: '{video.get('status')}'")

    # 2️⃣ SEGUNDO: Verificar/registrar en progress_manager
    state = await progress_manager.get_state(video_id)
    video_status = video.get("status")

    if not state:
        print(f"   📝 Video no está en progress_manager, registrándolo...")
        state = await progress_manager.register_video(video_id)
        
        # Set initial phase based on DB status
        status_to_phase = {
            "pending": ProcessingPhase.IDLE,
            "processing": ProcessingPhase.DETECTING,
            "detected": ProcessingPhase.VERIFYING,
            "verified": ProcessingPhase.WAITING_FOR_REVIEW, # DB: verified -> SSE: waiting_for_review
            "editing": ProcessingPhase.ANONYMIZING,         # DB: editing -> SSE: anonymizing
            "completed": ProcessingPhase.COMPLETED,
            "error": ProcessingPhase.ERROR
        }
        if video_status in status_to_phase:
            state.phase = status_to_phase[video_status]
            state.message = f"Video status: {video_status}"
            print(f"   ✅ Video registrado con fase: {state.phase.value}")
        else:
            print(f"   ✅ Video registrado en progress_manager (idle)")

    # 3️⃣ TERCERO: AUTO-START si el video está pendiente
    if video_status == "pending":
        print(f"   🚀 [AUTO-START] Video en estado 'pending', iniciando procesamiento...")

        file_path = video.get("original_path")
        if file_path:
            # Actualizar status a processing
            await db.update(db_video_id, {
                "status": "processing",
                "updated_at": datetime.now()
            })

            # Iniciar procesamiento en background
            asyncio.create_task(
                video_processor.process_full_pipeline(video_id, file_path)
            )
            print(f"   ✅ [AUTO-START] Procesamiento iniciado automáticamente")
        else:
            print(f"   ⚠️ [AUTO-START] No se encontró file_path para el video")
    elif video_status == "processing":
        print(f"   ℹ️ Video ya está procesándose")
    elif video_status == "verified":
        print(f"   ℹ️ Video esperando revisión del usuario (verified)")
        # El estado actual se enviará vía initial_state
    elif video_status == "editing":
        print(f"   ℹ️ Video en estado 'editing' (anonymizing)")
        # Check if anonymization is already running by checking state phase
        current_state = await progress_manager.get_state(video_id)
        if current_state and current_state.phase.value == "anonymizing":
            print(f"   ✅ Anonymization (editing) already in progress, waiting for events...")
        else:
            print(f"   ⚠️ Anonymization (editing) not started yet, will receive events when it starts")
    elif video_status in ["completed", "error"]:
        print(f"   ℹ️ Video ya terminó con status: {video_status}")
    else:
        print(f"   ℹ️ Video en estado: {video_status}")

    print(f"   ✅ SSE connection ready for {video_id}")

    return EventSourceResponse(
        content=event_generator(video_id, request),
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