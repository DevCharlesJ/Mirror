import socket

import PIL.Image
from PIL.Image import *
import pickle
from threading import Thread
from time import time, sleep
import os

from custom_socket import COMMUNICATION, CustomSocket

HEADER = 64
HOST = socket.gethostbyname(socket.gethostname())
PORT = 9666

OK_CODE = 200
ERR_CODE = 404

class Stream():
    first_addr = ()
    def __init__(self, socket_:CustomSocket):
        self.__socket_ = socket_

        self.imageThread:Thread = None
        # self.__snapshot:bytes = None
        self.__stream = [] # collection of streams, maintain stream length to be self.__MAX_STREAM_LENGTH + self.__garbage_size (350)
        self.__MAX_STREAM_LENGTH = 300
        self.__GARBAGE_SIZE = 50
        self.__num_garbage = 0
        self.__running = False
        self.__streamEndCallback = None

        self.__on_garbage_day_callback = None

    def getConnection(self):
        return self.__socket_

    def getLatestSnapshot(self) -> bytes:
        # Returns snapshot from the back
        try:
            return self.__stream[-1]
        except:
            return bytes()
        
    def getAvailableStreamLength(self) -> int:
        """Return the number of available streamed Image bytes in the array"""
        return len(self.__stream)-self.__num_garbage

    
    def getBufferedStream(self, start:int=0, buffer:int=1) -> list:
        try:
            available = self.getAvailableStreamLength() # elements from start to end
            if start > available:
                return []
            
            start += self.__num_garbage # account for garbage in splice
            reach = start+buffer
            #true_reach =  the lesser number between reach and what is available
            return self.__stream[start: reach if reach < available else available]
        except Exception as e:
            print(e)
            return []

    def setOnGarbageDay(self, callback):
        self.__on_garbage_day_callback = callback

    def __cleanGarbage(self):
        self.__stream = self.__stream[self.__num_garbage+1:] # a subset of stream where garbage is removed
        self.__num_garbage = 0

        if callable(self.__on_garbage_day_callback):
            self.__on_garbage_day_callback(self.__GARBAGE_SIZE)
    
    def isRunning(self): 
        return self.__running == True
    
    def setStreamEndCallback(self, callback):
        self.__streamEndCallback = callback if callable(callback) else None


    def start(self):
        if self.__running: return
        if not self.getConnection(): return

        self.__running = True
        self.__socket_.settimeout(3)

        def RI(): # recieve Image
            no_bytes = 0
            while self.__socket_ and self.__running and no_bytes < 3:
                # connection should send the length of the pickled image in bytes
                try:
                    
                    start = time()
                    self.__socket_.send_literal(1) # simple code tells connection to send a stream
                    snapshot = self.__socket_.recv()
                    assert snapshot

                    self.__stream.append((snapshot, time()-start))

                    if len(self.__stream) > self.__MAX_STREAM_LENGTH: # possible 1 frame of gargbe being included
                        self.__num_garbage += 1

                        if len(self.__stream) > self.__MAX_STREAM_LENGTH + self.__GARBAGE_SIZE:
                            self.__cleanGarbage()


                except Exception as e:
                    # input(e)
                    no_bytes += 1
                    # Socket_Tools.socket_send_literal(self.__conn, COMMUNICATION.CODES.ERROR) # SEND ERROR

            self.stop()

        self.imageThread = Thread(target=RI)
        self.imageThread.start()

        # wait 3 seconds for client to send first snapshot, cancel the stream
        elapsed_time = 0
        while len(self.__stream) == 0:
            if elapsed_time > 3:
                self.stop()
                break

            sleep(1)
            elapsed_time += 1

        


    def stop(self):
        if not self.__running: return
        
        try:
            self.__running = False
            self.imageThread.join()
        except: pass

        # WILL CHANGED TO SEND A CLOSED CODE later
        self.__socket_.send_literal(COMMUNICATION.CODES.ERROR)

        if callable(self.__streamEndCallback):
            self.__streamEndCallback()