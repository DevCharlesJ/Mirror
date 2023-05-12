import socket
import pickle

class COMMUNICATION:
    HEADER = 64
    HEADING_CHAR = ' '
    ENCODING = "utf-8"

    class CODES:
        OK = 200
        ERROR = 404
        NOOP = -1


class CustomSocket(socket.socket):
    __slots__ = () # Required for cast to work

    def __new__(cls, socket_=None):
        # This will cast socket object to a CustomSocket Object
        if isinstance(socket_, socket.socket):
            socket_.__class__ = CustomSocket
            return socket_
    
        object.__new__(cls)


    def __init__(self, socket_=None):
        if not socket_:
            super().__init__()


    def recv(self) -> bytes:
        try:
            # Noops should not be returned
            length = int(super().recv(COMMUNICATION.HEADER))
            bytes_ = bytes()
            
            while len(bytes_) < length:
                bytes_ += super().recv(length-len(bytes_))

            try:
                assert int(bytes_.decode(encoding=COMMUNICATION.ENCODING)) == COMMUNICATION.CODES.NOOP
                return self.recv() # recieved NOOP, return next recieve
            except:
                # Recieve was not NOOP, possible error with int cast or bytes_decoding
                # Need to handle decoding error?
                return bytes_ # return this recieve
        except:
            return bytes()
        
    def recv_decoded(self) -> str:
        bytes_ = self.recv()
        
        if bytes_:
            return bytes_.decode(encoding=COMMUNICATION.ENCODING)
        else:
            return ""
        
    def recv_literal(self):
        decoding = self.recv_decoded()
        if not decoding:
            return None

        try:
            return float(decoding) # return a number if conversion succeeds
        except:
            lowered = decoding.lower()
            if lowered == "true":
                return True
            elif lowered == "false":
                return False
            else:
                return decoding
        
    def recv_unpickled(self) -> object | None:
        try:
            return pickle.loads(self.recv())
        except:
            return None

    def send(self, bytes_:bytes):
        if not bytes_:
            bytes_ = bytes()

        try:
            super().send(bytes(f"{len(bytes_):{COMMUNICATION.HEADING_CHAR}>{COMMUNICATION.HEADER}}", encoding=COMMUNICATION.ENCODING)) # Send the length of bytes to expect
            super().send(bytes_) # send the bytes
        except: 
            pass

    def send_literal(self, literal):
        self.send(bytes( str(literal), encoding=COMMUNICATION.ENCODING))

    def noop(self):
        """Used to test connection and will return BaseException when connection failed"""
        bytes_ = bytes( str(COMMUNICATION.CODES.NOOP), encoding=COMMUNICATION.ENCODING)
        super().send(bytes(f"{len(bytes_):{COMMUNICATION.HEADING_CHAR}>{COMMUNICATION.HEADER}}", encoding=COMMUNICATION.ENCODING)) # Send the length of bytes to expect, could throw here
        super().send(bytes_) # send the bytes, and could trow here

    def send_pickled(self, object):
        if object is not None:
            self.send(pickle.dumps(object))
        



    # Overloads that ensure that instantiated base sockets are casted to CustomSocket
    def accept(self):
        conn, addr = super().accept()
        return CustomSocket(conn), addr
    
    def dup():
        return CustomSocket(super().dup())
