import socket
import pyaudio
import select
import threading

class AudioSender:

    def __init__(self, host, port, slots=8, audio_format=pyaudio.paInt16, channels=1, rate=44100, chunk=4096):
        self.__host = host
        self.__port = port

        self.__slots = slots
        self.__used_slots = 0
        self.__audio_format = audio_format
        self.__channels = channels
        self.__rate = rate
        self.__chunk = chunk
        self.__audio = pyaudio.PyAudio()
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__block = threading.Lock()
        self.__running = False

        self.__server_socket.bind((host, port))

    def start_stream(self):
        """
        Starts the server if it is not running already.
        """
        if self.__running:
            print("Server is already running")
        else:
            self.__running = True
            self.__stream = self.__audio.open(format=self.__audio_format, channels=self.__channels, rate=self.__rate, input=True, frames_per_buffer=self.__chunk, stream_callback=self.__callback)
            self.__read_list = [self.__server_socket]
            server_thread = threading.Thread(target=self.__server_listening)
            server_thread.start()

    def __server_listening(self):
        """
        Listens for new connections.
        """
        self.__server_socket.listen()
        while self.__running:
            self.__block.acquire()
            connection, address = self.__server_socket.accept()
            self.__read_list.append(connection)
            if self.__used_slots >= self.__slots:
                print("Connection refused! No free slots!")
                connection.close()
                self.__block.release()
                continue
            else:
                self.__used_slots += 1
            self.__block.release()
            thread = threading.Thread(target=self.__client_connection, args=(connection, address,))
            thread.start()

    def stop_server(self):
        """
        Stops the server and closes all connections
        """
        if self.__running:
            self.__running = False
            closing_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            closing_connection.connect((self.__host, self.__port))
            closing_connection.close()
            self.__block.acquire()
            self.__server_socket.close()
            self.__block.release()
        else:
            print("Server not running!")

    def __callback(self, in_data, frame_count, time_info, status):
        for s in self.__read_list[1:]:
            s.send(in_data)
        return (None, pyaudio.paContinue)

    def __client_connection(self, connection, address):
        """
        Handles the individual client connections and processes their stream data.
        """
        while self.__running:

            data = connection.recv(1024)
            if not data:
                self.__read_list.remove(connection)


class AudioReceiver:

    def __init__(self, host, port, audio_format=pyaudio.paInt16, channels=1, rate=44100, chunk=4096):
        self.__host = host
        self.__port = port
        self.__audio_format = audio_format
        self.__channels = channels
        self.__rate = rate
        self.__chunk = chunk
        self.__running = False
        self.__client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__audio = pyaudio.PyAudio()

    def __client_receiving(self):

        self.__client_socket.connect((self.__host, self.__port))
        while self.__running:
            data = self.__client_socket.recv(self.__chunk)
            self.__stream.write(data)


    def start_receiving(self):

        if self.__running:
            print("Client is already streaming!")
        else:
            self.__running = True
            self.__stream = self.__audio.open(format=self.__audio_format, channels=self.__channels, rate=self.__rate, output=True, frames_per_buffer=self.__chunk)
            client_thread = threading.Thread(target=self.__client_receiving())
            client_thread.start()

    def stop_stream(self):
        """
        Stops client stream if running
        """
        if self.__running:
            self.__running = False
        else:
            print("Client not streaming!")

rec = AudioReceiver("localhost", 4444)
rec.start_receiving()
