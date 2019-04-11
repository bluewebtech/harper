import cv2
import datetime
from devices import Devices
from stream import Stream
from tracker import Tracker
from http import server
import io
import logging
import numpy as np
import picamera
import socketserver
from threading import Condition
from threading import Thread

class StreamObject(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            self.buffer.truncate()

            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        stream = Stream()
        stream.setStream(output)

        tracker = Tracker()
        tracker.setStream(output)

        if self.path == '/':
            with open('templates/harper.html', 'rb') as fh:
                html = fh.read()
                content = html
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        if self.path == '/harper.css':
            with open('templates/harper.css', 'rb') as fh:
                html = fh.read()
                content = html
            self.send_response(200)
            self.send_header('Content-Type', 'text/css')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    stream.setLastSpeed(tracker.getLastSpeed())
                    stream.setSpeed(tracker.getSpeed())
                    stream.setSpeedInt(tracker.getSpeedInt())
                    stream.setMountColor(tracker.getMotionColor())
                    stream.setMonitoredBoundary(tracker.getMonitoredBoundary())

                    with output.condition:
                        output.condition.wait()

                    if stream.getStream() == None:
                        frame = output.frame
                    else:
                        frame = stream.getStream()

                    Thread(target=tracker.rawStream, args=()).start()
                    Thread(target=stream.liveStream, args=()).start()

                    # ret, frame = camera.read()
                    # ret, jpeg = cv2.imencode('.jpeg', frame)
                    # frame = jpeg.tobytes()

                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class Server(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    print('Harper has been started.')

# camera1 = cv2.VideoCapture(1)
output = StreamObject()

# print(Devices.get())

camera = picamera.PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
camera.hflip = False
camera.vflip = False
camera.start_recording(output, format = 'mjpeg')

try:
    address = ('0.0.0.0', 80)
    server = Server(address, StreamingHandler)
    server.serve_forever()
finally:
    # camera.release()
    camera.stop_recording()
    print('Harper has been stopped.')