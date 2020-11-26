import cv2
import socket
import pickle
import struct
import threading


class CameraServer:

    def __init__(self, host, port, slots=8):
        self.host = host
        self.port = port
        self.slots = slots
        self.used_slots = 0
        self.running = False
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_socket()

    def init_socket(self):
        self.server_socket.bind((self.host, self.port))

    def start_server(self):
        self.running = True
        while self.running:
            self.server_socket.listen()
            connection, address = self.server_socket.accept()
            thread = threading.Thread(target=self.client_connection, args=(connection,address,))
            thread.start()

    def stop_server(self):
        self.running = False

    def client_connection(self, connection, address):
        payload_size = struct.calcsize('>L')
        data = b""

        while self.running:

            while len(data) < payload_size:
                data += connection.recv(4096)

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]

            msg_size = struct.unpack(">L", packed_msg_size)[0]

            while len(data) < msg_size:
                data += connection.recv(4096)

            frame_data = data[:msg_size]
            data = data[msg_size:]

            frame = pickle.loads(frame_data, fix_imports=True, encoding="bytes")
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            cv2.imshow(str(address), frame)
            cv2.waitKey(1)

class CameraClient:

    def __init__(self, host, port):

        self.host = host
        self.port = port
        self.camera = cv2.VideoCapture(0)
        self.configure()
        self.running = False
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def configure(self):
        self.camera.set(3, 1000)
        self.camera.set(4, 1000)
        self.encoding_parameters = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    def stop_stream(self):
        self.running = False

    def start_stream(self):
        self.running = True
        self.client_socket.connect((self.host, self.port))
        while self.running:
            ret, frame = self.camera.read()
            result, frame = cv2.imencode('.jpg', frame, self.encoding_parameters)
            data = pickle.dumps(frame, 0)
            size = len(data)

            self.client_socket.sendall(struct.pack('>L', size) + data)

        self.camera.release()