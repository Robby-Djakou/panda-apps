#
#### app for Franka Emika Games
#
import queue
import warnings
import appController
import appModel
import appView
import threading
import os                   # for checking matrix file
import sys                  # used for exit()
import signal               # to catch Ctrl-C Interrupt
import queue                # 4 queues (between Controller and Model for Homeview and Tower of Hanoi, between Model and Controller, between Controller and Model and between Model and View for Tic-Tac-Toe and Checkers)
import logging
from config import *


# create logger
logger = logging.getLogger('appFrankaEmikaGames.py') 
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create log file
ch = logging.FileHandler('logs/appFrankaEmikaGmes.log', mode='w')

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)
 
class AppFrankaEmikaGames(threading.Thread):
    def __init__(self):
        """
        initialize the the necessary objects (e.g. Thread or Queue) for the Model, View, controller architecture:
        View: for the GUI with the Tkinter library
        Model: thread for the Comunication with the Franka Emika Robot, Camera Access
        Controller: thread for the Game Engine and CNNS detection and prediction

        :return: None
        """
        
        logger.debug("AppFrankaEmikaGames: init...")
        
        self.myAppModel = None
        self.myAppConroller = None
        self.myResultFrameQueue = queue.Queue(MAXLEN) # Queue for the camera frame Transmission between Model and View. The Goal is to use it for the Homeview and the tower of Hanoi Game View 
        self.myResultFrameQueue_Model_Controller = queue.Queue(MAXLEN) # Queue for the camera frame Transmission between Model and Controller. The Goal is to use this Frame for Game Engine in Controller (detection and prediction of the pieces for checkers and Tic-Tac-Toe)
        self.myResultFrameQueue_Controller_Model = queue.Queue(MAXLEN) # Queue for the transmission of the result frame between Controller and Model to give the user an overview of the detected game pieces.
        self.myResultFrameQueue_Games= queue.Queue(MAXLEN) # Queue for the transmission of the result frame between Model and View (this frame is for the Tic-Tac-Toe and Checkers View)
        
        self.lockForimshow = threading.Lock()   # lock object to protect imshow() 
        
        # filter warnings
        warnings.filterwarnings("ignore")

        self.event = threading.Event()  # used to stop threads, # create a event to allows communication between another threads
        signal.signal(signal.SIGINT, self.shutdown) # to interrupt the process by pressing Ctrl+C
        self.myAppModel = appModel.AppModel(self.event, self.myResultFrameQueue, self.myResultFrameQueue_Model_Controller, self.myResultFrameQueue_Controller_Model, self.myResultFrameQueue_Games, self.lockForimshow)
        self.myAppController = appController.AppController(self.event, self.myAppModel, self.myResultFrameQueue_Model_Controller, self.myResultFrameQueue_Controller_Model)
        
        # check if matrix file exists
        getCORNERSTicTT = not os.path.isfile(CORNERSTicTT) # get matrix of Tic Tac Toe gameboard for zoom 
        getCORNERSTABLE = not os.path.isfile(CORNERSTABLE_DATA) # get matrix of the 4 points on the Robot Table for calibration 
        getCORNERSCHECKERS = not os.path.isfile(CORNERSCHECKERS) # get matrix of checkers gameboard for zoom
        
        self.myAppView = appView.AppView(self.event, self.myResultFrameQueue, self.myResultFrameQueue_Games, getCORNERSTABLE, getCORNERSTicTT, getCORNERSCHECKERS, self.myAppController)

    def shutdown(self, sig, dummy):
        """
        to close the Mainthread for the AppFrankaEmikaGames.py and set the event to True, 
        that allow to also close other threads (e.g. appModel.py, appController.py or appView.py)
        """
        print ("Closing AppFrankaEmikaGames...")
        self.event.set() 
        sys.exit(0)

    def main(self):
        """
        starts all threads 
        
        :return: None
        """
        logger.debug("AppFrankaEmikaGames: starting...")
        self.myAppModel.start()
        self.myAppController.start()
        self.myAppView.startMainloop()    # mainloop Thread for TKinter GUI
        self.event.set()                  # kill other threads

myAppFrankaEmikaGames = AppFrankaEmikaGames()
myAppFrankaEmikaGames.main()

