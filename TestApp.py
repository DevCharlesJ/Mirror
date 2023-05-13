import sys
from threading import Thread
from time import sleep, time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow
)

from AppWidgets.Hub import Hub


import socket
from custom_socket import CustomSocket

# SIMPLE APPLICATION TO TEST STREAM OBSERVATION

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("APP TEST")
window.setMinimumSize(400,600)
window.setMaximumSize(window.minimumSize())

HUB:Hub = Hub()

window.setCentralWidget(HUB.UI)
window.show()



print("Testing App Startup")
HOST = input("Enter Server IPv4 Address: ")
PORT = int(input("Enter Port: "))


socket_ = CustomSocket(socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM))
socket_.settimeout(3)

socket_.connect((HOST,PORT))


socket_.send_literal(999) # IDENTIFY, CODE FOUND IN server.py -> CONNECTION_TYPE

if HUB:
    # GET List of (addrss, port, conn_type)
    def getStreamConnections() -> list:
        try:
            socket_.send_literal(f"getconnectioninfos")
            connections = []
            for info in socket_.recv_unpickled():
                ip, port, conn_type = info
                if conn_type == "streamer":
                    connections.append((ip, port))

            return connections
        except Exception as e:
            return []

    def updateStreamList():
        HUB.clearStreamList()
        connections = getStreamConnections()
        for connection in connections:
            HUB.newStream(name=f"{connection[0]} {connection[1]}")

    # HUB.setUpdateStreamList(updateStreamList)

    working = True
    last_recieve_rate = 0
    recieve_rate = 0
    stream_line = []
    stream_buffer = 10

    def playback():
        global stream_buffer, stream_line
        
        while working:
            if len(stream_line) > 0:
                showing = HUB.getShowingStream()
                if showing and HUB.UI.isStreamOpen():
                    try:
                        # start = time()
                        bytes_, when = stream_line.pop(0)
                        sleep(when)
                        HUB.setStreamImage(bytes_)
                        # print("Average rate is", (recieve_rate+last_recieve_rate)/2, end="\r") # get rate
                        #sleep((recieve_rate+last_recieve_rate)/2)
                        if HUB.getShowingStream() != showing: # showing changed
                            stream_line = []
                    except Exception as e:
                        print(e)
                        pass
                else:
                    stream_line = []
            else:
                HUB.setStreamImage(bytes()) # set playback to nothing (black screen)


            # sleep((recieve_rate+last_recieve_rate)/2)

    def worker():
        global recieve_rate, last_recieve_rate, stream_line, stream_buffer
        updateStreamList()
        tick = time()

        

        while working:
            showing = HUB.getShowingStream()
            if showing and HUB.UI.isStreamOpen():
                start = time()
                #  request image from address, specifying image count/buffer
                socket_.send_literal(f"getnextimagebuffer|{'|'.join(showing.split())}|{stream_buffer}")
                streamed_bytes:list = socket_.recv_unpickled() # will be list

                if streamed_bytes:
                    stream_line += streamed_bytes
                    recieve_rate = time()-start

            if time()-tick > 10: # every ten seconds
                updateStreamList()
                tick = time()

    workThread = Thread(target=worker)
    workThread.start()

    playbackThread = Thread(target=playback)
    playbackThread.start()




app.exec()
working = False
workThread.join()
playbackThread.join()
