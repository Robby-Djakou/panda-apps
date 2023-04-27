# videoStream.py
# class w/ separate thread to increase webcam streaming performance
# acc to https://pyimagesearch.com/2015/12/21/increasing-webcam-fps-with-python-and-opencv/
#
#
import threading
import cv2
import time
from config import *
import logging
from config import HEIGHT, WIDTH


# create logger
logger = logging.getLogger('videoStreamer.py') 
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create log file
ch = logging.FileHandler('logs/videoStreamer.log', mode='w')

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


class VideoStreamer(threading.Thread):
	def __init__(self, event):
		"""
		separate thread to increase grab-performance of webcam
		"""
		threading.Thread.__init__(self)  # call init of Parent-Class "Thread"
		# initialize the video camera stream and read the first frame
		# from the stream

		logger.debug("VideoStreamer: VideoStreamer init...")
		self.stream = None
		self.event = event
		self.stream = cv2.VideoCapture(CAPTUREDEVICE)
		time.sleep(0.5)
		if not self.stream is None and not self.stream.isOpened():
			logger.error("VideoStreamer: Cannot open usb camera, exit ...")
			self.event.set()
			exit()
		else:

			logger.debug("VideoStreamer: USB Camera is open ...")
			self.stream.set(cv2.CAP_PROP_EXPOSURE, 0)
			self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
			self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
			self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
			self.stream.set(cv2.CAP_PROP_FPS, FPS)
		(self.grabbed, self.frame) = self.stream.read()			

	def run(self):
		"""
		keep looping infinitely to grab current frame from camera until the thread is stopped
		"""
		while True:
			# if the thread indicator variable is set, stop the thread
			if self.event.is_set():
				logger.debug("VideoStreamer: thread stopped, exit ...")
				return

			# otherwise, read the next frame from the stream
			(self.grabbed, self.frame) = self.stream.read()
			

	def read(self):
		"""
		return the frame most recently read, called from outside thread by appModel
		"""
		return self.frame

	def setBrightness(self, newBrightness):
		"""
		adjust brigthness of webcam acc. to GUI slider
		"""
		newBrightness = int(newBrightness)
		self.stream.set(cv2.CAP_PROP_BRIGHTNESS, newBrightness)