from __future__ import print_function
from imutils.video.pivideostream import PiVideoStream
from datetime import datetime
import os
import imutils
import requests
import time
import sys
import numpy as np
import cv2


try: 
    SLACK_URL = os.environ['SLACK_URL']
    SLACK_TOKEN = os.environ['SLACK_TOKEN']
    SLACK_CHANNEL = os.environ['SLACK_CHANNEL']
except KeyError as e:
    sys.stderr.write('You need to set {} using Isaax.\n'.format(e))
    sys.stderr.write('See: https://isaax.io/manual/#/ja/environment-variables\n')
    sys.exit(1)

IMAGE_FILE = 'hello.jpg'

net = cv2.dnn.readNetFromCaffe('/home/pi/MobileNetSSD_deploy.prototxt.txt',
        '/home/pi/MobileNetSSD_deploy.caffemodel')


def upload():
    image = { 'file': open(IMAGE_FILE, 'rb') }
    payload = {
        'filename': IMAGE_FILE,
        'token': SLACK_TOKEN,
        'channels': [SLACK_CHANNEL],
    }
    requests.post(SLACK_URL, params=payload, files=image)


class Processor(object):
    def __init__(self, flip):
        self.vs = PiVideoStream(resolution=(800, 608)).start()
        time.sleep(2.0)
        self.flip = flip

    def __del__(self):
        self.vs.stop()

    def flip_if_needed(self, frame):
        if self.flip:
            return np.flip(frame, 0)
        return frame

    def is_detected(self):
        occupied = False
        frame = self.flip_if_needed(self.vs.read())
        frame = imutils.resize(frame, width=300)
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
        net.setInput(blob)
        detections = net.forward()
        for i in np.arange(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]

            if confidence < 0.2:
                continue

            idx = int(detections[0, 0, i, 1])
            if idx != 15:
                continue

            occupied = True
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startx, starty, endx, endy) = box.astype('int')
            cv2.rectangle(frame, (startx, starty), (endx, endy), (0, 255, 0), 2)
            y = starty - 15 if starty - 15 > 15 else starty + 15
            cv2.putText(frame, 'Person', (startx, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return occupied, frame


if __name__ == '__main__':
    last_uploaded = datetime.now()
    camera = Processor(flip=False) 

    while True:
        timestamp = datetime.now()
        occupied, frame = camera.is_detected() 
        if occupied:
            print('Someone is detected, Passed seconds: {}'.format((timestamp - last_uploaded).seconds))
            if (timestamp - last_uploaded).seconds >= 30:
                cv2.imwrite(IMAGE_FILE, frame)
                print('Uploading...')
                upload()
                last_uploaded = timestamp
                print('Finished.')

        time.sleep(1)
