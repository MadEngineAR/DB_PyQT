import socket


class MySocket(socket.socket):
    def __init__(self, *args, **kwargs):
        super(MySocket, self).__init__(*args, **kwargs)
        self.is_sender = bool
        self.is_listener = bool
