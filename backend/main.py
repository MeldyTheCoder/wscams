import typing
from time import perf_counter

import fastapi
import uvicorn
import fastapi_socketio
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, AudioStreamTrack
from aiortc.contrib.media import MediaPlayer
from fastapi.middleware.cors import CORSMiddleware

app = fastapi.FastAPI(
    debug=True,
    title="VSHPCams",
    description="🤫🤫🤫",
    version='1.4.8.8',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


socketio_app = fastapi_socketio.SocketManager(
    app=app,
    socketio_path='socket.io',
    mount_location='/',
    ping_timeout=15000,
    ping_interval=20000,
    always_connect=True,
)

COMPUTERS_NAMESPACE = '/cams'
FRONTEND_NAMESPACE = '/'


ConnectedComputersType = typing.Dict[str, typing.Dict[str, typing.Any]]
RTCConnectionDict = typing.Dict[str, RTCPeerConnection]

class ComputerManager:
    def __init__(self):
        self._connected_computers: ConnectedComputersType = {}
        self._rtc_connections = {}

    def set_computer(self, sid: str, name: str = None) -> dict:
        if sid in self._connected_computers:
            return self._connected_computers.copy()
        self._connected_computers[sid] = {'name': name or '???', 'id': sid}
        return self._connected_computers.copy()


    async def remove_computer(self, sid: str):
        computer_data = None

        if sid in self._connected_computers:
            computer_data = self._connected_computers[sid].copy()
            self.remove_rtc_computer(sid)
            del self._connected_computers[sid]

        return computer_data, self._connected_computers

    @property
    def connected_computers(self) -> ConnectedComputersType:
        return self._connected_computers.copy()

    @property
    def rtc_connections(self):
        return self._rtc_connections.copy()

    def create_rtc_cam_connection(self, sid: str, sdp: str, type: str):
        self._rtc_connections[sid] = {'sdp': sdp, 'type': type}
        return self._rtc_connections[sid]

    def remove_rtc_computer(self, computer_sid: str):
        if computer_sid not in self._rtc_connections:
            return

        del self._rtc_connections[computer_sid]


manager = ComputerManager()

@socketio_app.on('connect', namespace=COMPUTERS_NAMESPACE)
async def handle_computer_connect(sid: str, data: dict, auth: dict):
    """
    Обработчик подключений клиента камер с компов
    """

    cam_name = auth.get('computer_name', '???')
    print('[+] Новое подключение socket.io: ', cam_name)

    manager.set_computer(sid, cam_name)
    computer_data = manager.connected_computers[sid]

    await socketio_app.emit(
        event='computer_connected',
        data={
            "computer": {
                "id": sid,
                "name": computer_data["name"],
            },
            'computers': manager.connected_computers},
        namespace=FRONTEND_NAMESPACE
    )

@socketio_app.on(event='stream_data', namespace=COMPUTERS_NAMESPACE)
async def handle_computer_stream_to_frontend(sid: str, data: dict):
    sdp, type_ = data.get('sdp'), data.get('type')

    return await socketio_app.emit(
        event='stream',
        data={
            'sdp': sdp,
            'type': type_,
            'sid': sid,
        },
        namespace=FRONTEND_NAMESPACE,
        to=data.get('sid', ''),
    )

@socketio_app.on('request_stream', namespace=FRONTEND_NAMESPACE)
async def handle_request_camera_stream(sid: str, data: dict):
    computer_sid = data.get('sid')
    sdp, type_ = data.get('sdp'), data.get('type')

    return await socketio_app.emit(
        event='accept_offer',
        data={'sid': sid, 'sdp': sdp, 'type': type_},
        namespace=COMPUTERS_NAMESPACE,
        to=computer_sid,
    )


@socketio_app.on('send_message', namespace=FRONTEND_NAMESPACE)
async def handle_send_message_to_computer(_, data: dict):
    """
    Обработчик-отправитель сообщений из фронтенда на клиент компьютера
    """

    message, to_sid = data.get('message', ''), data.get('sid')
    if not to_sid:
        return None

    return await socketio_app.emit(
        event='message',
        to=to_sid,
        data={'message': message},
        namespace=COMPUTERS_NAMESPACE,
    )

@socketio_app.on('disconnect', namespace=COMPUTERS_NAMESPACE)
async def handle_computer_disconnect(sid: str):
    """
    Обработчик события отключение компа от сети
    """

    data, computers = await manager.remove_computer(sid)
    await socketio_app.emit(
        event='computer_disconnected',
        data={
            'computer': {
                'id': sid,
                'name': (data or {}).get('name', ''),
            },
            'computers': computers,
        },
        namespace=FRONTEND_NAMESPACE)


@socketio_app.on('connect', namespace=FRONTEND_NAMESPACE)
async def handle_frontend_connect(sid: str, *_):
    """
    Обработчик подключений фронтенда для моментального получения свежих данных компов.
    """

    print('[+] Новое подключение frontend: ', sid)
    return await socketio_app.emit(
        event='fetched',
        data={'computers': manager.connected_computers},
        to=sid,
        namespace=FRONTEND_NAMESPACE,
    )

if __name__ == "__main__":
    uvicorn.run(
        app=app,
        host='0.0.0.0',
        port=8080,
    )
