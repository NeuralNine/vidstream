import cv2
import numpy as np
import socket
import pickle
import struct
import threading
import pyautogui

class StreamingServer:

    def __init__(self, host, port, slots=8, quit_key='q'):
        self.__host = host
        self.__port = port
        self.__slots = slots
        self.__used_slots = 0
        self.__running = False
        self.__quit_key = quit_key
        self.__block = threading.Lock()
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__init_socket()

    def __init_socket(self):
        self.__server_socket.bind((self.__host, self.__port))

    def start_server(self):
        if self.__running:
            print("Server is already running")
        else:
            self.__running = True
            server_thread = threading.Thread(target=self.__server_listening)
            server_thread.start()

    def __server_listening(self):
        self.__server_socket.listen()
        while self.__running:
            self.__block.acquire()
            connection, address = self.__server_socket.accept()
            self.__block.release()
            thread = threading.Thread(target=self.__client_connection, args=(connection, address,))
            thread.start()

    def stop_server(self):
        self.__running = False
        closing_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        closing_connection.connect((self.__host, self.__port))
        closing_connection.close()
        self.__block.acquire()
        self.__server_socket.close()
        self.__block.release()

    def __client_connection(self, connection, address):
        payload_size = struct.calcsize('>L')
        data = b""

        while self.__running:

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
            if cv2.waitKey(1) == ord(self.__quit_key):
                connection.close()
                break


class CameraClient:

    def __init__(self, host, port, x_res=400, y_res=400):

        self.__host = host
        self.__port = port
        self.__camera = cv2.VideoCapture(0)
        self.__x_res = x_res
        self.__y_res = y_res
        self.__configure()
        self.__running = False
        self.__client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __configure(self):
        self.__camera.set(3, self.__x_res)
        self.__camera.set(4, self.__y_res)
        self.__encoding_parameters = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    def __client_streaming(self):
        self.__client_socket.connect((self.__host, self.__port))
        while self.__running:
            ret, frame = self.__camera.read()
            result, frame = cv2.imencode('.jpg', frame, self.__encoding_parameters)
            data = pickle.dumps(frame, 0)
            size = len(data)

            try:
                self.__client_socket.sendall(struct.pack('>L', size) + data)
            except ConnectionResetError:
                self.__running = False
            except ConnectionAbortedError:
                self.__running = False
            except BrokenPipeError:
                self.__running = False

        self.__camera.release()
        cv2.destroyAllWindows()

    def start_stream(self):
        if self.__running:
            print("Client is already streaming!")
        else:
            self.__running = True
            client_thread = threading.Thread(target=self.__client_streaming)
            client_thread.start()


class VideoClient:

    def __init__(self, host, port, video, loop=True):

        self.__host = host
        self.__port = port
        self.__video = cv2.VideoCapture(video)
        self.__configure()
        self.__running = False
        self.__loop = True
        self.__client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __configure(self):
        self.__video.set(3, 1000)
        self.__video.set(4, 1000)
        self.__encoding_parameters = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    def __client_streaming(self):
        self.__client_socket.connect((self.__host, self.__port))
        while self.__running:
            ret, frame = self.__video.read()
            result, frame = cv2.imencode('.jpg', frame, self.__encoding_parameters)
            data = pickle.dumps(frame, 0)
            size = len(data)

            try:
                self.__client_socket.sendall(struct.pack('>L', size) + data)
            except ConnectionResetError:
                self.__running = False
            except ConnectionAbortedError:
                self.__running = False
            except BrokenPipeError:
                self.__running = False

        self.__video.release()
        cv2.destroyAllWindows()

    def start_stream(self):
        if self.__running:
            print("Client is already streaming!")
        else:
            self.__running = True
            client_thread = threading.Thread(target=self.__client_streaming)
            client_thread.start()


class ScreenShareClient:

    def __init__(self, host, port, x_res=1024, y_res=576):

        self.__host = host
        self.__port = port
        self.__x_res = x_res
        self.__y_res = y_res
        self.__configure()
        self.__running = False
        self.__client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __configure(self):
        self.__encoding_parameters = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    def __client_streaming(self):
        self.__client_socket.connect((self.__host, self.__port))
        while self.__running:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (self.__x_res, self.__y_res), interpolation=cv2.INTER_AREA)
            result, frame = cv2.imencode('.jpg', frame, self.__encoding_parameters)
            data = pickle.dumps(frame, 0)
            size = len(data)

            try:
                self.__client_socket.sendall(struct.pack('>L', size) + data)
            except ConnectionResetError:
                self.__running = False
            except ConnectionAbortedError:
                self.__running = False
            except BrokenPipeError:
                self.__running = False

        cv2.destroyAllWindows()

    def start_stream(self):
        if self.__running:
            print("Client is already streaming!")
        else:
            self.__running = True
            client_thread = threading.Thread(target=self.__client_streaming)
            client_thread.start()