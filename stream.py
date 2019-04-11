import cv2
import datetime
from devices import Devices
from tracker import Tracker
from http import server
import io
import logging
import numpy as np
import picamera
import socketserver
from threading import Condition
from threading import Thread

SPEED_LIMIT = 35

class Stream:
  frame = None
  motionColor = ()
  lastSpeed = '0 mph'
  speed = '0 mph'
  speedInt = 0
  monitoredBoundary = None
  output = None

  def setStream(self, stream):
      self.output = stream

  def getStream(self):
      return self.frame

  def setMountColor(self, color):
    self.motionColor = color

  def setMonitoredBoundary(self, boundary):
    self.monitoredBoundary = boundary

  def setLastSpeed(self, speed):
    self.lastSpeed = speed

  def setSpeed(self, speed):
    self.speed = speed

  def setSpeedInt(self, speed):
    self.speedInt = speed

  def withBoundingBox(self, frame):
      return cv2.rectangle(frame, (140, 150), (500, 350), (255, 255, 255), 1)

  def withBoundingCrossHairs(self, frame):
      # top left horizontal
      frame = cv2.line(frame, (140, 150), (170, 150), (255, 255, 255), 1)
      # top left vertical
      frame = cv2.line(frame, (140, 150), (140, 180), (255, 255, 255), 1)

      # top right horizontal
      frame = cv2.line(frame, (470, 150), (500, 150), (255, 255, 255), 1)
      # top left vertical
      frame = cv2.line(frame, (500, 150), (500, 180), (255, 255, 255), 1)

      # bottom left horizontal
      frame = cv2.line(frame, (140, 350), (170, 350), (255, 255, 255), 1)
      # bottom left vertical
      frame = cv2.line(frame, (140, 350), (140, 320), (255, 255, 255), 1)

      # bottom right horizontal
      frame = cv2.line(frame, (470, 350), (500, 350), (255, 255, 255), 1)
      # bottom right vertical
      frame = cv2.line(frame, (500, 350), (500, 320), (255, 255, 255), 1)

      return frame

  def withTimestamp(self, frame):
    alpha = 0.6
    timestamp = datetime.datetime.now().strftime('%A %B %d, %Y at %I:%M:%S %p')
    overlay = frame.copy()
    cv2.rectangle(overlay, (15, 15), (305, 55), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    frame = cv2.putText(frame, timestamp, (25, 40), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1, cv2.LINE_AA)

    return frame

  def withCurrentSpeed(self, frame):
    speedLength = len(self.speed.replace(" ", ""))

    if (speedLength == 2):
      speedPosition = (555, 35)
    elif (speedLength == 3):
      speedPosition = (558, 35)
    else:
      speedPosition = (552, 35)

    alpha = 0.6
    timestamp = datetime.datetime.now().strftime('%A %B %d, %Y at %I:%M:%S %p')
    overlay = frame.copy()
    cv2.circle(overlay, (605, 35), 20, (0, 0, 0), -1, cv2.LINE_AA)
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    frame = cv2.circle(frame, (605, 35), 25, self.motionColor, 2, cv2.LINE_AA)
    frame = cv2.putText(frame, self.speed, speedPosition, cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1, cv2.LINE_AA)
    frame = cv2.putText(frame, 'MPH', (595, 48), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1, cv2.LINE_AA)

    return frame

  def withLastSpeed(self, frame):
    speedLength = len(self.speed.replace(" ", ""))

    if (speedLength == 2):
      speedPosition = (488, 35)
    elif (speedLength == 3):
      speedPosition = (488, 35)
    else:
      speedPosition = (488, 35)

    alpha = 0.6
    overlay = frame.copy()
    cv2.circle(overlay, (540, 35), 20, (0, 0, 0), -1, cv2.LINE_AA)
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    frame = cv2.circle(frame, (540, 35), 25, (255, 255, 255), 2, cv2.LINE_AA)
    frame = cv2.putText(frame, self.lastSpeed, speedPosition, cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1, cv2.LINE_AA)
    frame = cv2.putText(frame, 'MPH', (530, 48), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1, cv2.LINE_AA)

    return frame

  def liveStream(self):
      # ret, frame = camera.read()

      frame = self.output.frame
      frame = np.fromstring(frame, dtype=np.uint8)

      if len(frame) > 0:
          frame = cv2.imdecode(frame, 1)

          frame = self.withTimestamp(frame)
          frame = self.withCurrentSpeed(frame)
          frame = self.withLastSpeed(frame)
          frame = self.withBoundingCrossHairs(frame)

          if (self.speedInt > SPEED_LIMIT and self.monitoredBoundary):
              print(self.speedInt, SPEED_LIMIT, self.speedInt - SPEED_LIMIT)
              imageTimestamp = datetime.datetime.now().strftime('%Y-%m-%d_%I-%M-%S-%p')
              image = 'images/harper_' + imageTimestamp + '.jpg'
              cv2.imwrite(image, frame)

          ret, jpeg = cv2.imencode('.jpeg', frame)
          self.frame = jpeg.tobytes()