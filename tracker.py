import cv2
import datetime
import math
import numpy as np

DISTANCE = 65
FOV = 53.5

base_image = None

ix = 140
iy = 150
fx = 500
fy = 350

if fx > ix:
    upper_left_x = ix
    lower_right_x = fx
else:
    upper_left_x = fx
    lower_right_x = ix

if fy > iy:
    upper_left_y = iy
    lower_right_y = fy
else:
    upper_left_y = fy
    lower_right_y = iy

monitored_width = lower_right_x - upper_left_x
monitored_height = lower_right_y - upper_left_y

print("Monitored area:")
print(" upper_left_x {}".format(upper_left_x))
print(" upper_left_y {}".format(upper_left_y))
print(" lower_right_x {}".format(lower_right_x))
print(" lower_right_y {}".format(lower_right_y))
print(" monitored_width {}".format(monitored_width))
print(" monitored_height {}".format(monitored_height))
print(" monitored_area {}".format(monitored_width * monitored_height))

class Tracker:
    frame = None
    initial_time = ''
    initial_x = 0
    last_x = 0
    mph = 0
    state = 0
    last_mph = 0
    actual_speed = 0
    monitoredBoundary = None
    output = None

    def __init__(self):
        self.motion_detected_color = (0, 0, 255)

    def setStream(self, stream):
      self.output = stream

    def getLastSpeed(self):
        return "{:7.0f}".format(self.last_mph)

    def getSpeed(self):
        return "{:7.0f}".format(self.actual_speed)

    def getSpeedInt(self):
        return int("{:7.0f}".format(self.actual_speed))

    def getTrackSpeed(self, pixels, ftperpixel, secs):
        if secs > 0.0:
            return ((pixels * ftperpixel)/ secs) * 0.681818
        else:
            return 0.0

    def getElapsedTime(self, endTime, begTime):
        diff = (endTime - begTime).total_seconds()
        return diff

    def getMotionColor(self):
        return self.motion_detected_color

    def setMotionColor(self, color):
        self.motion_detected_color = color

    def setMonitoredBoundary(self, x, w, direction, monitored_width):
        self.monitoredBoundary = ((x <= 2) and (direction == 2)) or ((x + w >= monitored_width - 2) and (direction == 1))
        return self.monitoredBoundary

    def getMonitoredBoundary(self):
        return self.monitoredBoundary

    def rawStream(self):
        global base_image

        frame_width_ft = 2*(math.tan(math.radians(FOV * 0.5)) * DISTANCE)
        ftperpixel = frame_width_ft / float(640)
        speed = "{:7.0f} mph".format(0)
        thetime = datetime.datetime.now()

        frame = self.output.frame

        if len(frame) > 0:
            frame = np.fromstring(frame, dtype=np.uint8)
            frame = cv2.imdecode(frame, 1)

            # Crop the current frame based on the positions from the defined region of interest.
            # rect = cv2.rectangle(frame, (140, 150), (500, 350), (255, 255, 255), 1)
            frame = frame[150:350, 140:500]

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.GaussianBlur(frame, (15, 15), 0)

            if base_image is None:
                base_image = frame.copy().astype('float')

                lastTime = thetime
                self.output.buffer.truncate()

            # compute the absolute difference between the current image and
            # base image and then turn eveything lighter gray than THRESHOLD into
            # white
            frameDelta = cv2.absdiff(frame, cv2.convertScaleAbs(base_image))
            thresh = cv2.threshold(frameDelta, 15, 255, cv2.THRESH_BINARY)[1]

            # dilate the thresholded image to fill in any holes, then find contours
            # on thresholded image
            dilate = cv2.dilate(thresh, None, iterations=2)
            (cnts, _) = cv2.findContours(dilate.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

            # look for motion
            motion_found = False
            biggest_area = 0

            # examine the contours, looking for the largest one
            for c in cnts:
                (x1, y1, w1, h1) = cv2.boundingRect(c)

                # get an approximate area of the contour
                found_area = w1*h1
                # find the largest bounding rectangle
                if (found_area > 175) and (found_area > biggest_area):
                    biggest_area = found_area
                    motion_found = True
                    x = x1
                    y = y1
                    h = h1
                    w = w1

            if motion_found:
                self.setMotionColor((50, 205, 50))

                if self.state == 0:
                    self.state = 1
                    self.initial_x = x
                    self.last_x = x
                    self.initial_time = thetime

                    # print("x-chg    Secs      MPH  x-pos width")
                else:
                    secs = self.getElapsedTime(thetime, self.initial_time)

                    if secs >= 15:
                        self.state = 0
                        direction = 0
                        motion_found = False
                        biggest_area = 0
                        self.output.buffer.truncate(0)
                        base_image = None
                        # print('Resetting')
                        # continue

                    if self.state == 1:
                        if x >= self.last_x:
                            direction = 1
                            abs_chg = x + w - self.initial_x
                        else:
                            direction = 2
                            abs_chg = self.initial_x - x

                        self.mph = self.getTrackSpeed(abs_chg, ftperpixel, secs)
                        self.getSpeed()

                        # print("{0:4d}  {1:7.2f}  {2:7.0f}   {3:4d}  {4:4d}".format(abs_chg,secs, self.mph, x, w))

                        real_y = upper_left_y + y
                        real_x = upper_left_x + x

                        if self.setMonitoredBoundary(x, w, direction, monitored_width):
                            self.actual_speed = self.last_mph

                        self.last_mph = self.mph
                        self.last_x = x

            else:
                self.last_mph = 0
                self.mph = 0
                self.actual_speed = 0
                self.setMotionColor((0, 0, 255))