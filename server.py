import socket
from threading import Thread
from time import time, sleep
import os

from stream import Stream
from custom_socket import CustomSocket

class CONNECTION_TYPE:
    STREAMER = 1
    OBSERVER = 999

    @staticmethod
    def idTitle(id:int):
        if id == CONNECTION_TYPE.STREAMER:
            return "streamer"
        elif id == CONNECTION_TYPE.OBSERVER:
            return "observer"

class Connection():
    def __init__(self,server, socket_:CustomSocket, addr, conn_type:int):
        self.server = server
        self.socket_ = socket_
        self.addr = addr
        self.conn_type = conn_type
        self.__established = time()

    def whenEstablished(self):
        return float(self.__established)

    def close(self):
        self.socket_.close()

    def __repr__(self):
        return f"Addr: {self.addr}\nType: {self.conn_type}\nEstablished: {time()-self.__established} seconds ago"
    
class Connection_Handler():
    def __init__(self, connection:Connection):
        self.connection:Connection = connection
        self.__ended = False

    def hasEnded(self):
        return self.__ended == True

    def Go(self):
        pass

    def getServer(self):
        return self.connection.server

    def getConnectionType(self):
        return self.connection.conn_type
    
    def isStreamer(self):
        return self.getConnectionType() == CONNECTION_TYPE.STREAMER
    
    def isObserver(self):
        return self.getConnectionType() == CONNECTION_TYPE.OBSERVER
    
    def End(self):
        try:
            self.connection.socket_.close()
        except:
            pass
        finally:
            self.__ended = True
    
class Streamer(Connection_Handler):
    def __init__(self, connection:Connection):
        super().__init__(connection)
        self.stream = Stream(self.connection.socket_)
        self.stream.setOnGarbageDay(self.__onGarbageDay)
        self.observers = 0

        self.__address_stream_index = {} # A map of where an address is for its stream line | Key= (ip, port), Value=integer

    def setAddressStreamIndex(self,addr:tuple, index:int):
        if not isinstance(addr, tuple) or not isinstance(index, int):
            return
        
        self.__address_stream_index[addr] = index

    def getAddressStreamIndex(self,addr:tuple):
        return self.__address_stream_index.get(addr, 0)
    
    # TO BE CALLED BY STREAM
    def __onGarbageDay(self, garbage_removed:int):
        for addr in self.__address_stream_index.keys():
            index = self.getAddressStreamIndex(addr)
            if index > garbage_removed: # if index is passed garbage point
                # reduce garbage amount from index
                self.__address_stream_index[addr] = max(0, index-garbage_removed) # Using max just in case index goes negative, shouldn't happen

    def Go(self):
        self.stream.setStreamEndCallback(self.End)

        while not self.hasEnded():
            if not self.isStreamRunning():
                self.startStream()

                self.connection.socket_.send_literal("streamstart") # Tell socket_ to start sending bytes

                # wait 3 seconds for client to send first snapshot
                # if no snapshot, close the stream
                elapsed_time = 0
                while not self.hasEnded() and self.stream.getAvailableStreamLength() == 0:
                    if elapsed_time > 3:
                        self.stream.stop()
                        break

                    sleep(1)
                    elapsed_time += 1

    def onUpdateObservers(self):
        if self.observers <= 0:
            pass # Planning to keep streams going, but request a stream at a slower rate?. 
            #   They kinda forced on 3 second timeout on this version, then will wait 5 seconds of cool off time
            #   We can either try to work with it, or keep streams running as usual.
            #   This way they'll only cut off when the server turns off
            #   We can still save bandwith by delaying requests by 1 second, maybe two?
        else:
            if not self.isStreamRunning():
                self.startStream()

    def observerLeft(self, addr:tuple):
        self.__address_stream_index.pop(addr, None)
        self.observers -= 1
        self.onUpdateObservers()

    def observerJoined(self):
        self.observers += 1
        self.onUpdateObservers()


    def streamExists(self):
        return self.stream and self.stream.getConnection() != None

    def isStreamRunning(self):
        return self.stream and self.stream.isRunning()
    
    def startStream(self):
        if self.streamExists():
            self.stream.start()
    
    def stopStream(self):
        self.observers = 0
        self.stream.stop()

    def getBufferedStream(self, start:int, buffer:int) -> bytes:
        """Returns list of Image snapshots from stream with length of buffer or what is available"""
        return self.stream.getBufferedStream(start, buffer)
    
    def getLatestSnapshot(self) -> bytes:
        """Returns latest Image snapshot of stream from connection"""
        if not self.streamExists():
            return bytes()
        
        if not self.isStreamRunning():
            self.startStream()

        return self.stream.getLatestSnapshot()
    
    def getAvailableStreamLength(self) -> int:
        return self.stream.getAvailableStreamLength()
    
    def saveStreamedImage(self, file_path:str):
        """Saves latest snapshot of streamed Image to the given path"""
        pass


    def End(self):
        super().End()

        if self.stream.isRunning():
            self.stream.stop()

        

class Observer(Connection_Handler):
    def __init__(self, connection:Connection):
        super().__init__(connection)

    def Go(self):
        last_addr = () # ("x.x.xx", 0000)
    
        try:
            while not self.hasEnded():
                request = self.connection.socket_.recv_decoded()
                if not request:
                    if last_addr:
                        handler = self.getServer().getHandler(last_addr[0], int(last_addr[1]))
                        if handler and handler.isStreamer():
                            handler.observerLeft(self.connection.addr)

                        last_addr = ()

                    self.connection.socket_.noop() # check connectivity, can throw error 
                    continue


                if isinstance(request, str):
                    args = request.split("|")
                    if not args: continue
                    
                    if args[0] == "getconnectioninfos":
                        self.connection.socket_.send_pickled(self.getServer().getConnectionInfos())


                    elif args[0] == "getnextimagebuffer":
                        addr = (args[1], args[2])
                        buffer = int(args[3])

                        handler = None
                        addr_changed = last_addr != addr

                        if last_addr and addr_changed:
                            # let last stream know an observer has left its stream
                            last_handler = self.getServer().getHandler(last_addr[0], int(last_addr[1]))
                            if last_handler and last_handler.isStreamer():
                                last_handler.observerLeft(self.connection.addr)

                            last_addr = None


                        handler = self.getServer().getHandler(args[1], int(args[2]))
                        if addr_changed:
                            handler.setAddressStreamIndex(self.connection.addr, handler.getAvailableStreamLength())


                        if handler and handler.isStreamer():
                            if addr_changed:
                                handler.observerJoined()
                            last_addr = (args[1], args[2])

                        stream_index = handler.getAddressStreamIndex(self.connection.addr)
                        streamed_bytes = []
                        if handler:
                            # args[3] is the buffer
                            streamed_bytes = handler.getBufferedStream(start=stream_index, buffer=buffer)

                        # preceed index by the number of how many bytes elements were recieved
                        handler.setAddressStreamIndex(self.connection.addr, stream_index + len(streamed_bytes))
                        
                        self.connection.socket_.send_pickled(streamed_bytes)
        except Exception as e:
            print(e)
            pass

        # CONNECTION HAS ENDED

        if last_addr:
            handler = self.getServer().getHandler(last_addr[0], int(last_addr[1]))
            if handler and handler.isStreamer():
                handler.observerLeft(self.connection.addr)

            last_addr = ()

        if not self.hasEnded():
            self.End()


    def End(self):
        super().End()


class Server():
    def __init__(self, HOST:str, PORT:int):
        self.HOST = HOST
        self.PORT = PORT
        self.socket = CustomSocket(socket.create_server((HOST, PORT), family=socket.AF_INET))

        self.__connection_pool = {} # Key = Address, Val = (Connection_Handler isinstance, Thread)
        self.__running = False
        self.__newConnCallback = None

        self.__managerThread:Thread = None

    def setNewConnectionCallback(self, callback):
        if callable(callback):
            self.__newConnCallback = callback
        else:
            self.__newConnCallback = None

    def getConnectionInfos(self) -> list:
        """Returns list of 3-tuple (ip, xxxxx, conn_type title)"""
        infos = []
        for addr, value in self.__connection_pool.items():
            # value[0] is handler
            infos.append(
                (addr[0], addr[1], CONNECTION_TYPE.idTitle(value[0].getConnectionType()))
                )

        return infos


    def getStreamers(self) -> list:
        """Returns a list of Streamer addresses (2-tuple)"""

        addresses = []
        for addr, value  in self.__connection_pool.items():
            if value[0] and value[0].isStreamer():
                addresses.append(addr)

        return addresses

    def getHandler(self, ip:str, port:int) -> Connection_Handler | None:
        return self.__connection_pool.get((ip, port))[0]

    def getHandlersFromIP(self, ip:str) -> list:
        if not isinstance(ip, str):
            return []
        
        handlers = []
        for addr in self.__connection_pool.keys():
            if addr[0] == ip:
                handlers.append(self.__connection_pool[addr][0])

        return handlers
    
    def destroyConnection(self, addr:tuple):
        handler, thread = self.__connection_pool.get(addr)
        if handler and not handler.hasEnded():
            handler.End()

        try:
            thread.join() # nothing should prevent this thread from joining
        except:
            pass

        self.__connection_pool.pop(addr, None)
    
    def isRunning(self):
        return self.__running == True

    def start(self):
        self.__running = True

        def manageConnectionPool():
            while self.__running:
                if self.__connection_pool == {}:
                    continue

                for addr in tuple(self.__connection_pool):
                    value = self.__connection_pool.get(addr)
                    # print(value)
                    if value:
                        handler, thread = value
                        try:
                            if (not handler or handler.hasEnded()) or not thread:
                                self.destroyConnection(addr)
                        except Exception as e:
                            print(e)

        self.__managerThread = Thread(target=manageConnectionPool)
        self.__managerThread.start()

        while self.__running:
            print(f"{len(self.__connection_pool.keys())} Connections")
            try:
                conn, addr = self.socket.accept()
                assert addr not in self.__connection_pool

                conn.settimeout(3)
                conn_type = int(conn.recv_decoded())
                connection = Connection(self, conn, addr, conn_type)
                handler = None
                if conn_type == CONNECTION_TYPE.STREAMER:
                    handler = Streamer(connection)
                elif conn_type == CONNECTION_TYPE.OBSERVER:
                    handler = Observer(connection)

                if not handler:
                    # self.connections[addr] = Connection_Handler(connection)
                    raise Exception(f"Connection type from {addr} could not be identified")

                handlerThread = Thread(target=handler.Go)
                self.__connection_pool[addr] = (handler, handlerThread)
                handlerThread.start()

                # if not managerThread.is_alive():
                #     managerThread.run()
                
                self.__newConnCallback(connection)
            except Exception as e:
                conn.close()
                print(f"Connection refused!")
                print(f"REASON: {e.with_traceback(None)}")


        self.__managerThread.join()

    def shutdown(self):
        self.__running = False # Mark server as not running
        try:
            self.socket.close() # Stop accepting connections and communications
        except: pass

        try:
            self.__managerThread.join() # Wait for managerThread to join
        except: pass

        # All loops should've completed
        

        # Manually destroy each connection, and cleanup threads
        for addr in list(self.__connection_pool):
            self.destroyConnection(addr)



if __name__ == '__main__':
    try:
        os.chdir(os.path.dirname(__file__))
        
        print("Server Configuration")
        HOST = input("Enter Server IPv4 Address: ")
        PORT = int(input("Enter Port: "))
        
        server = Server(HOST, PORT)
        def onConnect(connection:Connection):
            print(f"New connection: \n{connection}")

        server.setNewConnectionCallback(onConnect)
        server.start()
    except Exception as e:
        input(e)