import fastapi
import uvicorn
import fastapi_socketio
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

connected_computers = {}

COMPUTERS_NAMESPACE = '/cams'
FRONTEND_NAMESPACE = '/'


def set_computer_picture(sid: str, picture: str, name: str = None) -> dict:
    computer_data = connected_computers.get(sid, None)
    if not computer_data:
        connected_computers[sid] = {'name': name or '???', 'picture': picture, 'id': sid}
    else:
        connected_computers[sid]['picture'] = picture

    return connected_computers.copy()


def remove_computer_data(sid: str):
    computer_data = None

    if sid in connected_computers:
        computer_data = connected_computers[sid].copy()
        del connected_computers[sid]

    return computer_data


@socketio_app.on('connect', namespace=COMPUTERS_NAMESPACE)
async def handle_computer_connect(sid: str, data: dict, auth: dict):
    """
    Обработчик подключений клиента камер с компов
    """

    # answer = await pc.createAnswer()
    # await pc.setLocalDescription(answer)
    #
    # socketio_app.emit("offer", answer, to=sid)

    cam_name = auth.get('computer_name', '???')
    print('New computer connection: ', sid, data, auth)
    data = set_computer_picture(sid, '', cam_name)
    await socketio_app.emit('cam_connected', {"cam_id": sid, "cam_name": cam_name}, namespace=FRONTEND_NAMESPACE)
    await socketio_app.emit('picture', data, namespace=FRONTEND_NAMESPACE)


async def send_message_callback(sid: str):
    return await socketio_app.emit('message_sent', to=sid, namespace=FRONTEND_NAMESPACE)


@socketio_app.on('send_message', namespace=FRONTEND_NAMESPACE)
async def handle_send_message_to_computer(sid: str, data: dict):
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


@socketio_app.on('cam', namespace=COMPUTERS_NAMESPACE)
async def handle_computer_picture_send(sid: str, data: dict):
    """
    Обработчик сигналов от клиента камер с компов на получение изображения с вебки.
    Далее данный обработчик вносит в словарь данные компа, в том числе снимок с экрана компа
    И отправляет его на фронт всем сразу.
    """

    data = set_computer_picture(sid, data.get('picture', ''))
    await socketio_app.emit('picture', data, namespace=FRONTEND_NAMESPACE)


@socketio_app.on('disconnect', namespace=COMPUTERS_NAMESPACE)
async def handle_computer_disconnect(sid: str):
    """
    Обработчик события отключение компа от сети
    """

    data = remove_computer_data(sid)
    await socketio_app.emit('cam_disconnected', {'cam_id': sid, 'cam_name': data['name']}, namespace=FRONTEND_NAMESPACE)
    await socketio_app.emit('picture', data=data, namespace=FRONTEND_NAMESPACE)


@socketio_app.on('connect', namespace=FRONTEND_NAMESPACE)
async def handle_frontend_connect(sid: str, data: dict):
    """
    Обработчик подключений фронтенда для моментального получения свежих данных компов.
    """

    print('New frontend connection: ', sid, data)
    await socketio_app.emit('picture', connected_computers.copy(), to=sid)

if __name__ == "__main__":
    uvicorn.run(
        app=app,
        host='0.0.0.0',
        port=8080,
    )
