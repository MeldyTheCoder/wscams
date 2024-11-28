import asyncio

import cv2
import fastapi
import uvicorn
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer
from av import VideoFrame
from fastapi.middleware.cors import CORSMiddleware

app = fastapi.FastAPI(debug=True)


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pcs = set()

@app.post("/offer")
async def offer(request: fastapi.Request):
    """
    Обработка SDP offer от клиента
    """
    params = await request.json()
    pc = RTCPeerConnection()
    pcs.add(pc)

    # Добавляем видеотрек с камеры
    video = MediaPlayer('/dev/video0')
    pc.addTrack(video.video)

    # Устанавливаем удаленное описание (offer)
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    await pc.setRemoteDescription(offer)

    # Создаем локальное описание (answer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return fastapi.responses.JSONResponse(content={
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    })


@app.on_event("shutdown")
async def on_shutdown():
    """
    Закрытие всех активных соединений при завершении работы сервера
    """
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    import uvicorn

    # Запуск FastAPI-сервера
    uvicorn.run(app, host="0.0.0.0", port=8080)