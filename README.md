# Stream
Testing a simple client-server model for sending and receiving streamed images

Uses simple socket traffic for communication. HTTP unsupported

## Start a Server
Either run server.py directly or import it and instantiate a Server object.
Then specify a valid IPv4 Address and Port. You cannot create multiple servers with the same IPv4 Address and Port

## Setup a Streamer
Creating streamer connections is easy.
Simply connect to your server and identify (Send '0' to identify as streamer). When you are ready to stream bytes, be sure to recieve 'streamstart' message from the server before you begin transmitting bytes. You have about ~3 seconds before the stream is closed by the server. You can check if a connection is still active by calling socket.noop(), which will raise an Exception if the connection has terminated.

### StreamerTest.py
You can run StreamerTest.py to initiate an example image stream loop (sends screenshots). You'll only need to specify the IPv4 Address and Port in order to connect to the server. Note that this script used the PIL libary to grab image data of from the screen and convert it to bytes

## Setup an Observer
An observer is another type of connection identity that can send commands to the server inorder to request data. Simply connect to your server and identify (Send '999' to identify as stream). Here are the following commands:
- 'getnextimagebuffer' => Returns a List of (image_bytes, when_recieved) streamed data specifying the streamers address and buffer (length of the array)
- 'getconnectioninfos' => Returns A List of (ip address, port) for each active streamer connected to the server

### TestApp.py
TestApp.py is a simple GUI application that graphically showcases the potential of an observer (for streamed images). The app will show a list of streamer connections which you can click to view its image stream. The list is refreshed every 10 seconds. PyQt6 is required for the application to run
