from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout
)
from PyQt6.QtGui import QPixmap, QAction
from PyQt6.QtCore import QByteArray

class Stream(QWidget):
    def __init__(self):
        super(Stream, self).__init__()

        self.vbox = QVBoxLayout()
        self.nameLbl = QLabel(text="A Stream")
        self.vbox.addWidget(self.nameLbl)
        self.previewLbl = QLabel()
        self.previewLbl.setPixmap(QPixmap(648, 486))
        self.vbox.addWidget(self.previewLbl)
        self.closeBtn = QPushButton("Close")
        self.vbox.addWidget(self.closeBtn)
        self.setLayout(self.vbox)

    def setName(self, name:str):
        if not isinstance(name, str):
            return
        
        self.nameLbl.setText(name)

    def setStreamImage(self, bytes_:bytes):
        try:
            pixmap = QPixmap(648, 486)
            pixmap.loadFromData(QByteArray(bytes_), format="JPEG")
            self.previewLbl.setPixmap(pixmap)
        except:
            pass

    def clearStreamImage(self):
        self.previewLbl.setPixmap(QPixmap(648, 486))
            

class HubUI(QWidget):
    def __init__(self):
        super(HubUI, self).__init__()

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)

        self.__stream_button = {} # Key: (addr, port) Value: QPushButton
        self.__stream:Stream = Stream()
        self.__stream.hide()
        self.__showingStream:str = ""


    def newStream(self, name):
        if name in self.__stream_button:
            return
        
        button = QPushButton(text=name)
        self.vbox.addWidget(button)
        button.setMinimumHeight(200)
        button.clicked.connect(lambda: self.showStream(name))
        self.__stream_button[name] = button

    def removeStream(self, name):
        if self.__stream.nameLbl.text() == name:
            self.__stream.hide()

        if name in self.__stream_button:
            button = self.__stream_button[name]
            self.vbox.removeWidget(button)

            self.__stream_button[name] = None

    def newStreamImage(self, bytes_:bytes):
        if not self.__stream or not isinstance(bytes_, bytes):
            return

        self.__stream.setStreamImage(bytes_)

    def clearStreamImage(self):
        self.__stream.clearStreamImage()

    def showStream(self, name):
        if not isinstance(name, str):
            return
        
        self.__stream.setName(name)        
        self.__stream.show()
        self.__showingStream = name

    def getShowingStream(self) -> str:
        return self.__showingStream
    
    def __onStreamClosed(self):
        self.__showingStream = ""

    def closeStream(self):
        self.__stream.hide()
        self.__onStreamClosed()

    def isStreamOpen(self):
        return self.__stream.isVisible()

    def clearStreamList(self):
        for name, button in self.__stream_button.items():
            if button:
                button.deleteLater()
            
        self.__stream_button = {}
        # self.closeStream()

    def streamExists(self, name) -> bool:
        return self.__stream_button.get(name) != None




    
class Hub:
    class ACTIONS:
        NEW_STREAM = 1
        REMOVE_STREAM = 2
        SET_STREAM_IMAGE = 3
        CLEAR_STREAM_IMAGE = 4
        CLEAR_STREAM_LIST = 5

        # @classmethod
        # def isAction(cls, action_code:int):
        #     return (
        #         action_code == cls.ADD_STREAM or
        #         action_code == cls.REMOVE_STREAM
        #     )
        

    def __init__(self):
        super(Hub, self).__init__()
        self.UI:HubUI = HubUI()

        self.__action = QAction()
        self.__action.triggered.connect(self.__onAction)
        self.__action_queue = [] # list of (Hub.ACTIONS, *args)


    def __onAction(self):
        if not self.__action_queue: return

        action, *args = self.__action_queue.pop(0)

        if action == Hub.ACTIONS.SET_STREAM_IMAGE:
            if len(args) == 1:
                self.UI.newStreamImage(args[0])
        elif action == Hub.ACTIONS.CLEAR_STREAM_IMAGE:
            self.UI.clearStreamImage()
        elif action == Hub.ACTIONS.NEW_STREAM:
            if len(args) == 1:
                self.UI.newStream(args[0])

    def __newHubAction(self, action_code:int, *args):
        self.__action_queue.append((action_code, *args))
        self.__action.trigger()
        





    # ACTIONS THAT WOULD REQIURE THREADED ACTIVITY, IN SAME THREAD
    def setStreamImage(self, bytes_:bytes):
        self.__newHubAction(Hub.ACTIONS.SET_STREAM_IMAGE, bytes_)

    def clearStreamImage(self):
        self.__newHubAction(Hub.ACTIONS.CLEAR_STREAM_IMAGE)

    def newStream(self, name:str, joinCallback=None) -> Stream:
        if not isinstance(name, str): return
        self.__newHubAction(Hub.ACTIONS.NEW_STREAM, name)


    # DIRECT CALLS
    def streamExists(self, name:str) -> bool:
        return self.UI.streamExists(name)

    def getShowingStream(self) -> str:
        return self.UI.getShowingStream()

    def removeStream(self, name:str):
        self.UI.removeStream(name)

    def clearStreamList(self):
        self.UI.clearStreamList()
