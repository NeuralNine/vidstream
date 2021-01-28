"""
This module implements the main functionality of vidstream.

Author: Florian Dedov from NeuralNine
YouTube: https://www.youtube.com/c/NeuralNine
"""

__author__ = "Florian Dedov, NeuralNine"
__email__ = "mail@neuralnine.com"
__status__ = "planning"

import cv2
import pyautogui
import numpy as np

import socket
import pickle
import struct
import threading
from ffpyplayer.player import MediaPlayer
from vidstream.exceptions import VidStreamError


CAMERA_STREAM = 1
VIDEO_STREAM = 2
SCREEN_SHARE_STREAM = 3

class StreamingServer:
    """
    Class for the streaming server.

    Attributes
    ----------

    Private:

        __host : str
            host address of the listening server
        __port : int
            port on which the server is listening
        __slots : int
            amount of maximum avaialable slots (not ready yet)
        __used_slots : int
            amount of used slots (not ready yet)
        __quit_key : chr
            key that has to be pressed to close connection
        __running : bool
            inicates if the server is already running or not
        __block : Lock
            a basic lock used for the synchronization of threads
        __server_socket : socket
            the main server socket


    Methods
    -------

    Private:

        __init_socket : method that binds the server socket to the host and port
        __server_listening: method that listens for new connections
        __client_connection : main method for processing the client streams

    Public:

        start_server : starts the server in a new thread
        stop_server : stops the server and closes all connections
    """

    # TODO: Implement slots functionality
    def __init__(self, host, port, slots=8, quit_key='q'):
        """
        Creates a new instance of StreamingServer

        Parameters
        ----------

        host : str
            host address of the listening server
        port : int
            port on which the server is listening
        slots : int
            amount of avaialable slots (not ready yet) (default = 8)
        quit_key : chr
            key that has to be pressed to close connection (default = 'q')  
        """
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
        """
        Binds the server socket to the given host and port
        """
        self.__server_socket.bind((self.__host, self.__port))
    
    def start_server(self):
        """
        Starts the server if it is not running already.
        """
        if self.__running:
            print("Server is already running")
        else:
            self.__running = True
            server_thread = threading.Thread(target=self.__server_listening)
            server_thread.start()

    def __server_listening(self):
        """
        Listens for and accepts new connections.
        """
        self.__server_socket.listen()
        while self.__running:
            self.__block.acquire()
            connection, address = self.__server_socket.accept()
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
            with self.__block:
                self.__server_socket.close()

        else:
            print("Server not running!")

    def __client_connection(self, connection, address):
        """
        Handles the individual client connections and processes their stream data.
        """
        payload_size = struct.calcsize('>L')
        data = b""

        while self.__running:

            break_loop = False

            while len(data) < payload_size:
                received = connection.recv(4096)
                if received == b'':
                    connection.close()
                    self.__used_slots -= 1
                    break_loop = True
                    break
                data += received

            if break_loop:
                break

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
                self.__used_slots -= 1
                break


class StreamingClient:
    """
    Abstract class for the generic streaming client.

    Attributes
    ----------

    Private:

        __host : str
            host address to connect to
        __port : int
            port to connect to
        __running : bool
            inicates if the client is already streaming or not
        __encoding_parameters : list
            a list of encoding parameters for OpenCV
        __client_socket : socket
            the main client socket


    Methods
    -------

    Private:

        __client_streaming : main method for streaming the client data

    Protected:

        _configure : sets basic configurations (overridden by child classes)
        _get_frame : returns the frame to be sent to the server (overridden by child classes)
        _cleanup : cleans up all the resources and closes everything

    Public:

        start_stream : starts the client stream in a new thread
    """

    def __init__(self, host, port):
        """
        Creates a new instance of StreamingClient.

        Parameters
        ----------

        host : str
            host address to connect to
        port : int
            port to connect to
        """
        self.__host = host
        self.__port = port
        self.__running = False
        self._capture = None
        self.__encoding_parameters = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        self.__client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _configure(self):
        """
        Basic configuration function.
        """
        pass

    def _get_frame(self):
        """
        Basic function for getting the next frame.

        Returns
        -------

        flag : flag denoting the source of the frame(default = None)
        frame : the next frame to be processed (default = None)
        """
        return None, None

    def _cleanup(self):
        """
        Cleans up resources and closes everything.
        """
        if isinstance(self._capture, cv2.VideoCapture):
            self._capture.release()
        cv2.destroyAllWindows()

    def __client_streaming(self):
        """
        Main method for streaming the client data.
        """
        self.__client_socket.connect((self.__host, self.__port))
        tracker = 0
        while self.__running:
            source, frame = self._get_frame()
            if frame is not None:
                tracker = 1
                if source == CAMERA_STREAM:
                    frame = cv2.flip(frame, 1)
                    height = frame.shape[0]
                    width = frame.shape[1]
                    cv2.circle(frame, (80, height-50), 20, (0, 0, 255), -1)
                    cv2.circle(frame, (80, height-50), 24, (255, 255, 255), 2)
                    cv2.putText(frame, 'Live', (115, height-37), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
                result, frame = cv2.imencode('.jpg', frame, self.__encoding_parameters)
                data = pickle.dumps(frame, 0)
                size = len(data)

                try:
                    self.__client_socket.sendall(struct.pack('>L', size) + data)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    # All caught in the same except clause to shorten code
                    self.__running = False
            else:
                # raise a friendly exception
                if tracker == 0:
                    # No initial frame was read
                    self.__running = False
                    self._cleanup()
                    raise VidStreamError('''Check that your camera is connected properly if using external camera or check that the correct index is given. If videostreaming, you might want to provide a video of supported type''')
                else:
                    # The video (feed) is over and there are no more frames to read
                    self._cleanup()

        self._cleanup()

    def start_stream(self):
        """
        Starts client stream if it is not already running.
        """

        if self.__running:
            print("Client is already streaming!")
        else:
            self.__running = True
            client_thread = threading.Thread(target=self.__client_streaming)
            client_thread.start()

    def stop_stream(self):
        """
        Stops client stream if running
        """
        if self.__running:
            self.__running = False
        else:
            print("Client not streaming!")


class CameraClient(StreamingClient):
    """
    Class for the camera streaming client.

    Attributes
    ----------

    Private:

        __host : str
            host address to connect to
        __port : int
            port to connect to
        __running : bool
            indicates if the client is already streaming or not
        __encoding_parameters : list
            a list of encoding parameters for OpenCV
        __client_socket : socket
            the main client socket
        __cam_index : int
            the index of the camera to use
        __x_res : int
            the x resolution
        __y_res : int
            the y resolution

    Protected:
    _capture : VideoCapture
        the camera object

    Methods
    -------

    Protected:

        _configure : sets basic configurations
        _get_frame : returns the camera frame to be sent to the server
        _cleanup : cleans up all the resources and closes everything

    Public:

        start_stream : starts the camera stream in a new thread
    """

    def __init__(self, host, port, cam_index=0, x_res=1024, y_res=576):
        """
        Creates a new instance of CameraClient.

        Parameters
        ----------

        host : str
            host address to connect to
        port : int
            port to connect to
        x_res : int
            the x resolution
        y_res : int
            the y resolution
        cam_index : int
            index of the camera to use
        """
        super(CameraClient, self).__init__(host, port)
        self.__x_res = x_res
        self.__y_res = y_res
        self.__cam_index = cam_index
        self._capture = cv2.VideoCapture(self.__cam_index)
        self._configure()

    def _configure(self):
        """
        Sets the camera resolution and the encoding parameters.
        """
        self._capture.set(3, self.__x_res)
        self._capture.set(4, self.__y_res)
        super(CameraClient, self)._configure()

    def _get_frame(self):
        """
        Gets the next camera frame.

        Returns
        -------

        flag : flag denoting the source of the frame
        frame : the next camera frame to be processed
        """
        ret, frame = self._capture.read()
        return CAMERA_STREAM, frame



class VideoClient(StreamingClient):
    """
    Class for the video streaming client.

    Attributes
    ----------

    Private:

        __host : str
            host address to connect to
        __port : int
            port to connect to
        __running : bool
            indicates if the client is already streaming or not
        __encoding_parameters : list
            a list of encoding parameters for OpenCV
        __client_socket : socket
            the main client socket
        __loop : bool
            boolean that decides whether the video shall loop or not

    Protected:
        _capture : VideoCapture
            the video object

    Methods
    -------

    Protected:

        _configure : sets basic configurations
        _get_frame : returns the video frame to be sent to the server
        _cleanup : cleans up all the resources and closes everything

    Public:

        start_stream : starts the video stream in a new thread
    """

    def __init__(self, host, port, video, loop=True):
        """
        Creates a new instance of VideoClient.

        Parameters
        ----------

        host : str
            host address to connect to
        port : int
            port to connect to
        video : str
            path to the video
        loop : bool
            indicates whether the video shall loop or not
        """
        super(VideoClient, self).__init__(host, port)
        self._capture = cv2.VideoCapture(video)
        self.__player = MediaPlayer(video)
        self.__loop = loop
        self._configure()

    def _configure(self):
        """
        Set video resolution and encoding parameters.
        """
        self._capture.set(3, 1024)
        self._capture.set(4, 576)
        super(VideoClient, self)._configure()

    def _get_frame(self):
        """
        Gets the next video frame.

        Returns
        -------

        flag : flag denoting the source of the frame
        frame : the next video frame to be processed
        """
        ret, frame = self._capture.read()
        audio_frame, val = self.__player.get_frame()
        return VIDEO_STREAM, frame


class ScreenShareClient(StreamingClient):
    """
    Class for the screen share streaming client.

    Attributes
    ----------

    Private:

        __host : str
            host address to connect to
        __port : int
            port to connect to
        __running : bool
            indicates if the client is already streaming or not
        __encoding_parameters : list
            a list of encoding parameters for OpenCV
        __client_socket : socket
            the main client socket
        __x_res : int
            the x resolution
        __y_res : int
            the y resolution


    Methods
    -------

    Protected:

        _get_frame : returns the screenshot frame to be sent to the server

    Public:

        start_stream : starts the screen sharing stream in a new thread
    """

    def __init__(self, host, port, x_res=1024, y_res=576):
        """
        Creates a new instance of ScreenShareClient.

        Parameters
        ----------

        host : str
            host address to connect to
        port : int
            port to connect to
        x_res : int
            the x resolution
        y_res : int
            the y resolution
        """
        self.__x_res = x_res
        self.__y_res = y_res
        self._configure()
        super(ScreenShareClient, self).__init__(host, port)

    def _get_frame(self):
        """
        Gets the next screenshot.

        Returns
        -------

        flag : flag denoting the source of the frame
        frame : the next screenshot frame to be processed

        """
        screen = pyautogui.screenshot()
        frame = np.array(screen)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (self.__x_res, self.__y_res), interpolation=cv2.INTER_AREA)
        return SCREEN_SHARE_STREAM, frame
