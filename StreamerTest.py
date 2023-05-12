import socket
from PIL import ImageGrab
from time import sleep
from io import BytesIO
from custom_socket import CustomSocket

def main():
    print("StreamerTest Startup")
    HOST = input("Enter Server IPv4 Address: ")
    PORT = int(input("Enter Port: "))

    socket_ = CustomSocket(socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM))
    socket_.settimeout(3)
    socket_.connect((HOST,PORT))
    socket_.send_literal(0) # IDENTIFY, CODE FOUND IN server.py -> CONNECTION_TYPE

    with BytesIO() as bio:
        try:
            resolution = (648, 486)
            while True:
                check = socket_.recv_literal()
                if check and int(check) == 1:
                    ImageGrab.grab().resize(resolution).save(bio, "JPEG") # screenshot and save to bytesio
                    bio.seek(0)
                    socket_.send(bio.read()) # send jpg bytes
                    bio.flush()
                    bio.seek(0)
                else:
                    socket_.noop() # can throw error
                    sleep(5)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    try:
        main()
    except Exception as e: 
        input(e)
        pass
    