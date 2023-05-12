import socket
from PIL import ImageGrab
from io import BytesIO
from custom_socket import CustomSocket

def main():
    print("StreamerTest Startup")
    HOST = input("Enter Server IPv4 Address: ")
    PORT = int(input("Enter Port: "))

    socket_ = CustomSocket(socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM))
    socket_.settimeout(3)
    socket_.connect((HOST,PORT))
    socket_.send_literal(1) # IDENTIFY, CODE FOUND IN server.py -> CONNECTION_TYPE

    with BytesIO() as bio:
        try:
            resolution = (648, 486)
            status = socket_.recv_literal()
            assert status == "streamstart" # Server is ready to recieve stream
            
            while True:
                ImageGrab.grab().resize(resolution).save(bio, "JPEG") # screenshot and save to bytesio
                bio.seek(0)
                socket_.send(bio.read()) # send jpg bytes, can throw error if connection terminated
                bio.flush()
                bio.seek(0)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    try:
        main()
    except Exception as e: 
        input(e)
        pass
    