#
### appController.py 
# implements controller component of MVC architecture of Franka Emika Games
# implement the games algorithms of Tic-Tac-Toe, Tower of hanoi and checkers game
# use a queue of camera frames from model to perform the detection the gameboards and the games pieces 
# generates an array from frames and sends it to games algorithms.
# result frames will be send to Model 
import os
import threading                
import logging
import time
from TowerofHanoiView import * # another view to visualize the evolution of the türme of hanoi game.
import numpy as np
import cv2
from config import *
import random
from copy import deepcopy 
from pygame import mixer
from keras.models import load_model # to load a trained model for keras
import torch # to load trained yolov5 model
import checkers # minimax and alpha-beta-pruning for checkers game 
import _thread

# create logger
logger = logging.getLogger('appController.py') 
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create log file
ch = logging.FileHandler('logs/appController.log', mode='w')

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

class AppController(threading.Thread):
    def __init__(self, event, observerModel, myResultFrameQueue_Model_Controller, myResultFrameQueue_Controller_Model):

        threading.Thread.__init__(self)  # call init of Parent-Class "Thread"
        """
        class to implement controller component of Franka Emika Games app
        :param: event 
        :param: observerModel
        :param: myResultFrameQueue_Model_Controller
        :param: myResultFrameQueue_Controller_Model 
        
        :return: create the Controller Component
        """
        logger.debug("AppController: appController init...")
        self.myResultFrameQueue_Model_Controller = myResultFrameQueue_Model_Controller
        self.myResultFrameQueue_Controller_Model = myResultFrameQueue_Controller_Model
        self.storage = None
        self.event = event
        self.observerModel= observerModel     # AppController acts as Observable, observer is appModel
        self.observerView = None              # AppController acts as 2nd Observable, observer appView is registered after it is availalbe
        self.brightness = 0 
        self.cornersTableData = None # calibration matrix of the four points on the table 
        self.gameName = None # to define the name of the started game, to stop the game process and the camera frames when the view of the game is closing
        self.stopFPSHomeView = False
        mixer.init()
        self.voiceCmdSpeaker = "espeak -v english-us -a 190 -p 70 -s 120 -m '{}' --stdout | aplay & "
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.debug("Using Device for detection of pieces: {}".format(self.device))
        self.appName = None  # to notify the appModel, to send the camera frame only one Queue for the current started game

        ##### tower of hanoi
        self.dataTOH=[] # informations of the user inputs for the tower of hanoi from appView
        self.stateTOH = [] # Contains the results of the tower of hanoi algorithm about which disc was moved from which position to which position.
        self.counter_TOH = 0 # the number of moves during tower of hanoi game

        ##### checkers game 
        self.cornersdataCheckers = None # calibration matrix to zoom on checkers game board
        self.stopFPSCheckers = False 
        self.scoreCheckers = [0,0] # user and panda robot scores
        self.levelCheckers = 1 # level of game to difficult
        self.stopgameCheckers = False # to stop the checkers game
        self.modelCheckers = self.load_modelCheckers(MODEL_CHECKERS) # load trained yolov5 model for detection with bounding-box of checkers pieces
        self.classesCheckers = self.modelCheckers.names # load labels of checkers pieces (white or black)
        self.dictCheckers = {} # to store the pixel coordinates of the centers from the 64 fields of the game board
        self.indexs1 = None # get index of player pieces from the last saved arrays of checkers game board
        self.indexs2 = None # get index of player pieces from the current detected arrays of checkers game board
        self.viaPiece  = [] # saved the pixel coordinates of the player's pieces that have been jumped
        self.getCenterofFieldsCheckers = None
        self.circleData = None # coordinates of the center of circular piece outside the playing field.
        self.matrix = None # array of the checkers game

        ##### Tic-Tac-Toe game
        self.stopFPSTicTT = False
        self.scoreTicTT = [0,0]    # user and panda robot scores
        self.levelTicTT = 1 # level of game to difficult
        self.choose_user = True  # set of true if the user play and false if the camputer play
        self.player = None # player symbol ('X' for player)
        self.computer = None # computer symbol ('O' for computer)
        self.initGame = False # to initialize the move of computer if a new symbol from user in tic-tac-toe gameboard has been detected 
        self.last_time = 0
        self.write_comp = False # help to write computer symbol on virtual tic-tac-toe gameboard
        self.board = [' ' for x in range(9)] # create the tic-tac-toe gameboard
        self.stopgameticTT = False # to stop the checkers game 
        self.center_coordPixel = None # to save the pixel coordinate of center of a tic-tac-toe field
        self.cornersdataTicTT = None # calibration matrix to zoom on tic-tac-toe gameboard
        self.modelTicTT = load_model(MODEL_TIC_TAC_TOE) # load trained keras model for classification of tic-tac-toe pieces
        self.autoStartTicTT = False # set to true if the current tic-tac-toe game is finish (win/lost/tie game) to start a new game automatically
        self.counterIndexTicTT = [] # to copy the current arrays of the tic-tac-toe game field and verify if the the new array differt from this copy. If this case then there is a new piece from the computer in the game board.
        self.stopNotifyObserverModel_TicTT_HomeView = False # set true to stop notifying the model 
        
    def doAudio(self, textOutput = None, waitBevor=False):
        """
        play text input with audio by using espeak
        :param: textOutput: text to play
        :waitBevor: wait 3 seconds bevor to read the text 
        
        :return: None 
        """
        if waitBevor:
            time.sleep(3)         
        if (not textOutput is None and SPEAKAUDIO == True) :
            voiceCmd = self.voiceCmdSpeaker.format(textOutput)
            os.system(voiceCmd)
        return
    
    def playAudio(self, audiofilename):
        """
        play audio file with mixer
        :param: audiofilename: 
      
        :return: None 
        """
        alert = mixer.Sound(audiofilename)
        alert.play()

    def registerObserverView(self, observerView):
        """
        called by appView to register as observerView
        
        :return: None
        """
        self.observerView= observerView

    def updateHomeView(self, brightness=0, stopFPSHomeView = False, cornersTableData = None, appName = None):
        """
        will be used from view to notify the controller about the update informations from the home view

        :return: None
        """
        self.brightness = brightness
        self.stopFPSHomeView = stopFPSHomeView
        self.cornersTableData = cornersTableData
        self.appName = appName
        self.notifyObserverModel_TicTT_HomeView()

    ############################################ Tower of Hanoi begin ############################################
    def notifyObserverModel_TOH(self):
        """
        to notify the observer (appModel) with values:
        - counter_TOH: Anzahl von Zügen (Bewegungen) bis zu Ergebnisse
        - dataTOH: content the enter information (from Pegs, to Pegs, temporyPegs) of the user, the Pixel coordinate of the 3 towers and the disc number
        - stateTOH: the different movements and positions involved. 
        - appName: to notify that Tower of hanoi view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running

        :return: None 
        """
        logger.debug("AppController Tower of Hanoi: notifyObserverModel_TOH")
        self.observerModel.update_TOH(counter_TOH = self.counter_TOH, dataTOH = self.dataTOH, stateTOH = self.stateTOH, appName = self.appName)
    
    def startGameTOH(self):
        """
        to start the tower of hanoi for the Model and start a new View of tower of hanoi to display the Problem-Solving Progression 

        :return: None
        """
        logger.debug("AppController Tower of Hanoi: tower of hanoi game has been started!")
        self.hanoi(self.dataTOH[0], self.dataTOH[1], self.dataTOH[2], self.dataTOH[3]) # get Solving information of the tower of hanoi for the Model
        self.notifyObserverModel_TOH() # to notify the model
        try:
            _thread.start_new_thread(Tkhanoi(self.dataTOH[0], self.dataTOH[1], self.dataTOH[2], self.dataTOH[3]).run(), ()) # start in a new Thread a the new view of Problem-Solving Progression 
        except:
            logger.error("Exit Tower of Hanoi from appController !")
        self.dataTOH  = [] # if the robot finisched to solve the current tower of hanoi problem, set all the variable to empty
        self.stateTOH = []
        self.counter_TOH = 0
        #self.appName = None
        #self.notifyObserverModel_TOH()
    
    def updateTOH(self,  dataTOH = None, appName = None):
        """
        transfert the input values of user from the view to the model
        - dataTOH: content the enter information (from Pegs, to Pegs, temporyPegs) of the user, the Pixel coordinate of the 3 towers and the disc number
        - appName: to notify that Tower of hanoi view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running

        :return: None
        """
        logger.debug("AppController Tower of Hanoi: tower of hanoi update the Model")
        self.dataTOH = dataTOH
        self.appName = appName
        self.notifyObserverModel_TicTT_HomeView()
    
    def hanoi(self, disknumber, fromPegs, toPegs, temporaryPegs):
        """
        Algorithm to solve the tower of hanoi problem with the use of recursive function.
        - disknumber: The number of discs entered by the user. 
        - fromPegs: The starting point where the discs are located at the beginning of the game.
        - toPegs: The end point where the discs are located at the end of the game.
        - temporaryPegs: The transhipment point for discs

        :return: None
        """
        logger.debug("AppController Tower of Hanoi: tower of hanoi Algorithm")
        if disknumber <= 0:
            return
        self.counter_TOH +=1
        self.hanoi(disknumber-1, fromPegs, temporaryPegs, toPegs)
        self.stateTOH.append((disknumber, fromPegs, toPegs))
        self.hanoi(disknumber-1, temporaryPegs, toPegs, fromPegs)
    ############################################ Tower of Hanoi end ############################################
    
    ############################################ checkers game begin ############################################
    def position_computer(self):
        """
        Defines in the arrays for the checkers game board the positions of the pieces of computer ("c") with the index (i,j)

        :return: None
        """
        logger.debug("AppController checkers game: set computer pieces into arrays")
        for i in range(3):
            for j in range(8):
                if (i + j) % 2 == 1:
                    self.mat[i][j] = ("c" + str(i) + str(j))

    def position_player(self):
        """
        Defines in the arrays for the checkers game board the positions of the pieces of player ("b") with the index (i,j)

        :return: None
        """
        logger.debug("AppController checkers game: set player pieces into arrays")
        for i in range(5, 8, 1):
            for j in range(8):
                if (i + j) % 2 == 1:
                    self.mat[i][j] = ("b" + str(i) + str(j))
    
    def load_modelCheckers(self, model_name):
        """
        load model with torch from the local directory "./yolov5"

        :return: model: loaded model for the detection of checkers pieces (white and black pieces)
        """
        logger.debug("AppController checkers game: load model for the detection of checkers pieces")
        model = torch.hub.load(DIRECTORY_MODEL_CHECKERS, 'custom', path=model_name, source='local')
        return model
    
    def notifyObserverModel_Checkers(self):
        """
        to notify the observer (appModel) with values:
        - cornersdataCheckers: transformation matrix for Checkers View to zoom on game board
        - stopFPSCheckers: to hide FPS during calibration
        - appName: to notify that Tic Tac Toe view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running

        :return: None 
        """
        logger.debug("AppController checkers game: send configurations values (transformation matrix and function to hide FPS to model")
        self.observerModel.update_Checkers(cornersdataCheckers = self.cornersdataCheckers, stopFPSCheckers= self.stopFPSCheckers, appName = self.appName)

    def notifyObserverModel_Checkers_Robot(self):
        """
        to notify the observer (appModel) with values:
        - xy_coord_From: The pixel coordinates of the piece to be moved
        - xy_coord_To: The pixel coordinates of the position where the piece is to be moved.
        - viaPiece: if available, the player's pieces that have been jumped

        :return: None 
        """
        logger.debug("AppController checkers game: send the pixel coordinates to Model about the movents of computer in game board")
        self.observerModel.update_Checkers_Robot(xy_coord_From = self.xy_coord_From, xy_coord_To = self.xy_coord_To, viaPiece = self.viaPiece)
    
    def startGameCheckers(self):
        """
        to start a new checkers game:

        :return: None 
        """
        logger.debug("AppController checkers game: a new checkers Game is starting ...")
        self.playAudio(GAMESTART)
        self.mat = [[], [], [], [], [], [], [], []] # initializes an empty array to save the initial positions of pieces for the checkers game
        
        # Fills all indexes of the array with "---" (means no pieces)
        for row in self.mat:
            for i in range(8):
                row.append("---")
        self.position_computer() # set computer pieces to array
        self.position_player() # set player pieces to array
        self.dictionaryCheckers = {} # is used to compare if the position of player pieces from the last saved arrays and the position of player pieces from the current detected arrays are same or not.
        self.dictionaryCheckersPiecesFrom = {} # to get the start position (x,y) of the player piece who has been moved to send it to checkers algorithm 
        self.dictionaryCheckersPiecesTo = {} # # to get the end position (x,y) of the player piece who has been moved to send it to checkers algorithm 

        """
        There are two ways to start the checkers game as shown in the view, 
        a new game of Checkers with initial position of Checkers Pieces or
        to start a saved state of the game.
        If the matrix at the start of the game is None, 
        then it means that the user does not want to load 
        a saved state of the game. But if the matrix is not empty, 
        then it means that the user wants to continue a saved state of the game.
        """
        if self.matrix is None:
            logger.debug("AppController checkers game: a new checkers Game is starting ...")
            self.matrix = np.array(self.mat) # convert arrays of game field in numpy arrays
            self.checkers = checkers.Checkers(self,self.matrix) # AppController acts as Observable, observer is Checkers
        else:
            logger.debug("AppController checkers game: a checkers part is continuing ...")
            self.checkers = checkers.Checkers(self,self.matrix)
        self.gameName = "Checkers" # set the name of the game to checkers to send Frame only to Checkers view
        self.scoreCheckers = [0,0] # initialize score of payer with index 0 and Franka robot with index 1
        _thread.start_new_thread(self.doAudio, ("Welcome to Checkers Game",)) # play welcome message with audio during the starting of checkers game
        _thread.start_new_thread(self.doAudio, ("you can play now", True)) # the second argument (True) defines a timeout of 3 seconds so that the new text message can been played to notify the player that he can play now
        self.notifyObserverViewCheckers(newScore= self.scoreCheckers) # send the initial score to view
        self.stopgameCheckers = False # to stop game 
        self.dictCheckers = {}
        self.viaPiece  = []
        self.notifyObserverViewCheckers(message = "Checkers Game is starting ...")
    
    def continueGameCheckers(self):
        """
        continue a saved checkers game state

        :return: None
        """
        logger.debug("AppController checkers game: continue a saved checkers game state")
        if os.path.isfile(SAVE_STATE_CHECKERS_GAME): # verify if the file "data/continue_save_state_Checkers.npy" exists
            arr = np.load(SAVE_STATE_CHECKERS_GAME, allow_pickle=True) # if the file exists load this 
            if len(arr) != 0:
                self.matrix = arr[1] # load the saved matrix of a saved checkers game state and copy this into self.matrix
                self.startGameCheckers() # start a new game with the saved state of checkers game
            else:
                logger.error("AppController checkers game: the file `continue_pause.npy` is corrupted")
                self.notifyObserverViewCheckers(message = "Please delete manually the file `continue_pause.npy` in Folder `data` and try again!")
        else:
            logger.error("AppController checkers game: the file `continue_pause.npy` don't exist")
            self.notifyObserverViewCheckers(message = "Can't find any saved checkers game state. Please start a new game and save it state!")

    def saveStateGameCheckers(self):
        """
        save the current checkers game state

        :return: None
        """
        logger.debug("AppController checkers game: the current game will be saving ...")
        if self.matrix is None:
            logger.error("AppController checkers game: the game state can't be saved if the matrix is None")
            self.notifyObserverViewCheckers(message="Please start a new Game and save it state !")
        else:
            logger.debug("Current checkers game state has been saved ...")
            matrix_new = [self.levelCheckers, self.matrix]
            np.save(SAVE_STATE_CHECKERS_GAME, matrix_new)
            self.notifyObserverViewCheckers(message = "Current checkers game state has been saved ...")
    
    def stopCheckers(self):
        """
        stop checkers game, stop to send frame to the checkers view and initialize the matrix to None

        :return: None
        """
        logger.debug("AppController checkers game: current checkers game has been stopped!")
        self.stopgameCheckers= True
        self.gameName = None# set the current opened windows to None
        self.matrix = None
    
    def notifyObserverViewCheckers(self, newScore= None, message = None):
        """
        notify the view with the current scores and the notifications process of the checkers game

        :return: None
        """
        logger.debug("AppController checkers game: notify view with current scores and notifications of the game process")
        self.observerView.updateCheckersView(newScoreCheckers=newScore, message = message)
    
    def updateCheckers(self, stopFPSCheckers= False, levelCheckers = 1, cornersdataCheckers = None, appName = None, getCenterofFieldsCheckers = None, use_getCenterofFields = 1):
        """
        will be used from view to notify the controller about the update informations from the checkers view

        :return: None
        """
        self.levelCheckers = levelCheckers
        self.cornersdataCheckers = cornersdataCheckers
        self.appName = appName
        self.getCenterofFieldsCheckers = getCenterofFieldsCheckers
        self.use_getCenterofFields = use_getCenterofFields
        self.stopFPSCheckers = stopFPSCheckers
        self.notifyObserverModel_Checkers()

    def findBiggestContour(self, mask):
        """
        get biggest Contour of the detected part in binary image
        :param: mask: binary images or frames

        :return: contours: detected contrours
        """
        temporaryArray = []
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if len(contours) == 0:
            return False
        for cnt in contours:
            temporaryArray.append(cv2.contourArea(cnt))
        greatest = max(temporaryArray)
        index_bigCNTS = temporaryArray.index(greatest)
        key = 0
        for cnt in contours:
            if key == index_bigCNTS:
                return cnt
                
            key += 1

    def score_frame(self, frame):
        """
        use the yolov5 model to detect the game pieces
        :param: frame: BGR frame 

        :return: label of detected game piece and the position of this game piece on the image 
        """
        self.modelCheckers.to(self.device)
        frame = [frame]
        results = self.modelCheckers(frame)
        labels, cord = results.xyxyn[0][:, -1], results.xyxyn[0][:, :-1]
        return labels, cord

    def class_to_label(self, x):
        """
        for a label, return the corresponding string label.
        :param: x: label

        :return: self.classesCheckers[int(x)]: string label
        """
        return self.classesCheckers[int(x)]

    def plot_boxes(self, results, frame):
        """
        take a frame with its results and display bounding boxes and label
        :param: result: labels and coordinates predicted by model
        :param: frame: frame 
        
        :return: frame with bounding box around detected object
        """
        labels, cord = results
        n = len(labels)
        x_shape, y_shape = frame.shape[1], frame.shape[0]
        for i in range(n):
            row = cord[i]
            if row[4] >= 0.5:
                x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape)
                bgr = (0, 255, 0)
                x1, y1, x2, y2 = x1+5, y1+5, x2-5, y2-5
                cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, 1)
        return frame


    def getGameFieldCheckers(self, coord, frame):
        """
        cropped a part of a frame with the giving coordinates
        :param: coord: pixels coordinates of the part, that will be cropped
        :param: frame: frame 
        
        :return: crop_img: cropped part of the image
        """
        crop_img = frame[int(coord[0]): int (coord[1]),int(coord[2]):int(coord[3])]
        return crop_img

    def rectContrains(self, bl, tr, p):
        """
        verify if the point p is into the rectangle coordinates bl and tr 
        :param: bl: first array of pixel coordinates of rectangle area.
        :param: tr: second array of pixel coordinates of rectangle area.

        :return: True: if the point  p is into the area with coordinates bl, tr
                 False: if the point p is not into the area with coordinates bl, tr
        """
        if (p[0] >= bl[0] and p[0] <= tr[0] and p[1] >= bl[1] and p[1] <= tr[1]):
            return True
        else: 
            return False  

    def getPlayerCheckers(self, points, frame):
        """
        get the move of player piece on the game board from the camera frame 
        :param: points: center pixels coordinates of the rectangle area of the 64 fields
        :param: frame: RGB frame

        :return: None 
        """
        self.indexs1 = np.flatnonzero(np.char.startswith(self.matrix, 'b')) # get index of the value, that beginnt with b (player piece) from the current gameboard
        results = self.score_frame(frame) # get label with pixel coordinates 

        self.arr  = [] # define array to save the current state of gameboard with the camera

        self.curr_state = np.array([['---' for col in range(8)] for row in range(8)]) # create a leer (---) array game board
        
        self.array1 = []  
        labels, cord = results 
        n = len(labels)
        x_shape, y_shape = frame.shape[1], frame.shape[0]
        for k in range(n):
            row = cord[k]
            if row[4] >= 0.5:
                x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape) # get the pixels coordinates of the detected classe
                x1, y1, x2, y2 = x1+5, y1+5, x2-5, y2-5 # reduce border of the bounding box
                self.array1.append([(x1, y1, x2, y2), self.class_to_label(labels[k])]) # save the pixels coordinates of the detected game piece on frames and the string of this label 
        
        
        """
        verify if the center coordinates of each field of the game board inside the detected rectangle bounding box,
        to save the current position of the detected game piece into the array self.arr
        """
        for i in range (len(points)):
            result = False
            for rect in (self.array1):
                result = self.rectContrains((rect[0][0], rect[0][1]), (rect[0][2], rect[0][3]), points[i])
                if result == True: # if center point inside the bounding box, then get the string of label of this bounding box and write this into the array self.arr
                    label = rect[1]
                    self.arr.append(label)
                    break
            if result == False: # if none bounding box, then the field in the gameboard has not a piece (add None when not piece detected into a field)
                self.arr.append(None)


        """
        use self.arr with the current state of gameboard to create a numpy array which will be understood by the checker algorithm. 
        the value of this numpy array (self.curr_state) are cxy for computer pieces (white), bxy for player pieces (black) and --- for none piece.
        self.curr_state ist two-dimensional array

        for the x, y pixels coordinates of each position into the numpy array self.curr_state, the center coordinate of this position must be assigned 
        """
        try:
            count = 0
            for i in range (8):
                for j in range (8):
                    if self.arr[count] == 'white':
                        self.curr_state[i][j] = f'c{i}{j}'.format(j=j, i=i)
                    elif self.arr[count] == 'black':
                        self.curr_state[i][j] = f'b{i}{j}'.format(j=j, i=i)
                    elif self.arr[count] == None:
                        pass
                    coord = points[count]
                    self.dictCheckers['{i}{j}'.format(i=i,j=j)] = coord # save the center coordinate of the i,j-position of numpy array curr_state 
                    count +=1
        except:
            logger.error("AppView: error by created the array of the current gameboard state in the getPlayerCheckers()-function")


        self.indexs2 = np.flatnonzero(np.char.startswith(self.curr_state, 'b'))# get index of the value, that beginnt with b (player piece) from the detected gameboard by the camera
        

        compare = np.array_equal(self.indexs1, self.indexs2) # compare these 2 arrays (if True then equal, if False then not equal)

        # use a dictionary to count the result value of comparaison
        self.dictionaryCheckers[compare] = self.dictionaryCheckers.get(compare,0) + 1 
        maxCounted = max(self.dictionaryCheckers, key = self.dictionaryCheckers.get)

        if (self.dictionaryCheckers[maxCounted] ==  2) : # if the same value comes two time, then verify if the value is False or True 
            if maxCounted == False: # if False, then the two state array gameboard are different  
                try:           
                    diff_value_from = np.setdiff1d(self.indexs1, self.indexs2) # get the  difference of two arrays and return the unique values in self.indexs1 that are not in self.indexs2. the different value is the position of the player piece that has been moved.
                    diff_value_to = np.setdiff1d(self.indexs2, self.indexs1) # cible position of the moved piece 
                    
                    # extract and prepare informations for the algorithm 
                    fromInd1 = str(self.matrix.flatten()[diff_value_from][0])[1:2] # extract the x pixel coordinate of the start position of the player piece that has been moved.
                    fromInd2 = str(self.matrix.flatten()[diff_value_from][0])[2:3] # extract the y pixel coordinate of the start position of the player piece that has been moved.
                    toInd1 = str(self.curr_state.flatten()[diff_value_to][0])[1:2] # extract the x pixel coordinate of the cible position of the moved player piece.
                    toInd2 = str(self.curr_state.flatten()[diff_value_to][0])[2:3] # extract the y pixel coordinate of the cible position of the moved player piece.
                    
                    fromInd = fromInd1 + "," + fromInd2
                    toInd = toInd1 + "," + toInd2

                    # use a dictionary to count the value of start position and cible position of the moved piece
                    self.dictionaryCheckersPiecesFrom[fromInd] = self.dictionaryCheckersPiecesFrom.get(fromInd,0) + 1
                    self.dictionaryCheckersPiecesTo[toInd] = self.dictionaryCheckersPiecesTo.get(toInd,0) + 1
                    maxCountedPiecesFrom = max(self.dictionaryCheckersPiecesFrom, key = self.dictionaryCheckersPiecesFrom.get)
                    maxCountedPiecesTo = max(self.dictionaryCheckersPiecesTo, key = self.dictionaryCheckersPiecesTo.get)


                    # if the same value of the start position and cible position comes 2 times
                    if (self.dictionaryCheckersPiecesFrom[maxCountedPiecesFrom] == 2) and (self.dictionaryCheckersPiecesTo[maxCountedPiecesTo] == 2):
                        self.notifyObserverViewCheckers(message="a Move was found !") # notify the view about the move of player
                        
                        # verify if the user activate or disable the mandatory jumps in view 
                        if self.levelCheckers == 1: # if mandatory jumps activate 
                            fromMove1, fromMove2, toMove1, toMove2, viaPiece, matrix  = self.checkers.play(maxCountedPiecesFrom, maxCountedPiecesTo, mandatory_jumping=True) # send the start position and cible position of moved player piece to minimax and alpha beta pruning algorithm
                        elif self.levelCheckers == 0:# if mandatory jumps disable  
                            fromMove1, fromMove2, toMove1, toMove2, viaPiece, matrix  = self.checkers.play(maxCountedPiecesFrom, maxCountedPiecesTo, mandatory_jumping=False)


                        self.matrix = matrix # copy the returned matrix from algorithm to the current matrix of the class
                        self.matrix = np.array(self.matrix) # convert the matrix list to numpy array
                    
                        self.xy_coord_From = self.dictCheckers['{i}{j}'.format(i=fromMove1, j=fromMove2)] # save the pixel start position of the piece that has been moved by the computer into the variable self.xy_coord_From for appModel
                        self.xy_coord_To = self.dictCheckers['{i}{j}'.format(i=toMove1, j=toMove2)] # save the pixel cible position of the piece that has been moved by the computer into the variable self.xy_coord_To for appModel

                        if len(viaPiece) != []: # if a player piece has been jumped by the computer
                            for i in viaPiece:
                                self.viaPiece.append(self.dictCheckers['{j}'.format(j=i)]) # save the pixel coordinate of the position of the jumped piece into the array self.viaPiece for appModel

                        self.notifyObserverModel_Checkers_Robot() # notify the appModel with the new pixel coordonates informations of positions  
                        
                        # initialize to 0 all the previous variable
                        self.viaPiece = [] 
                        self.dictionaryCheckersPiecesFrom[maxCountedPiecesFrom] = 0
                        self.dictionaryCheckersPiecesTo[maxCountedPiecesTo] = 0
                        self.dictionaryCheckersPiecesFrom = {}
                        self.dictionaryCheckersPiecesTo = {}

                        self.dictionaryCheckers[maxCounted] = 0
                        self.dictionaryCheckers = {}

                    # if the same value of the start position and cible position comes more than 2 times, then initialize the counter to null
                    if (self.dictionaryCheckersPiecesFrom[maxCountedPiecesFrom] >= 2) or (self.dictionaryCheckersPiecesTo[maxCountedPiecesTo] >= 2):
                        self.dictionaryCheckersPiecesFrom[maxCountedPiecesFrom] = 0
                        self.dictionaryCheckersPiecesTo[maxCountedPiecesTo] = 0
                        self.dictionaryCheckersPiecesFrom = {}
                        self.dictionaryCheckersPiecesTo = {}              
                        self.dictionaryCheckers[maxCounted] = 0
                        self.dictionaryCheckers = {}
                except:
                    logger.error("AppView: error by getting the start and cible position of the moved piece of player in getPlayerCheckers()-function")
        
        # if the count the result value of comparaison between self.indexs1 and  self.indexs2 comes more than 2 time, then initialize the counter to null
        elif ( self.dictionaryCheckers[maxCounted] >= 2) :
            self.dictionaryCheckers[maxCounted] = 0  
            self.dictionaryCheckers = {}
        




    def getCentersFields(self, frame):
        """
        function to get the centers of fields of the checker gameboard, when the player has cliked on the button  "Get Centers now" in the view
        :param: frame: BGR frame 

        :return: frame with the detection of the 64 centers of all fields in checker gameboard
        """
        arr_centroids = []
        fields = []
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, frame_thresh = cv2.threshold(
            frame_gray, 170, 255, cv2.THRESH_BINARY_INV) # convert gray frames to binary frames
        cnt = self.findBiggestContour(frame_thresh)
        self.x,self.y,h,w = cv2.boundingRect(cnt) # get biggest contour (contour of gameboard)
        column = w/8 # divide with of detected gameboard into 8 column
        line = h/8 # divide height of detected gameboard into 8 rows
        points = [] 

        """
        determine the coordinates to get each field of the checker gameboard
        """
        for num_column in range(0,9):
            for num_line in range(0,9):
                points.append(((num_line*line)+self.x,(num_column*column)+self.y))

        for number in range(0, 71):
            if number != 8 and number != 17 and number != 26 and number != 35 and number != 44 and number != 53 and number != 62:
                field = [points[number][1], points[number+10][1], points[number][0],points[number+10][0]]
                fields.append(field)

        # calculate with the previous coordinates the centers of each field of checker gameboard and save it into arr_centroids
        if len(fields) != 0:
            for i in range (len(fields)):
                coord = (int((fields[i][2]+ fields[i][3])/2), int((fields[i][0]+fields[i][1])/2))
                arr_centroids.append(coord)

            # display the centers coordinates of each field into the frame
            for k in arr_centroids:
                frame = cv2.circle(frame, k  , 10, (0, 0, 255), -1)
            
            self.arr_centroids = arr_centroids

        return frame 


    def runCheckers_AutomaticallyDetection(self, frame):
        """
        automatic detection auf gameboard and game piece
        :param: frame: camera frames from appModel

        :return: frame: result frames with detection of game board and game pieces
        """
        frame_copy = frame.copy()

        arr_centroids = []  # to save the middle positions of each fields (64 fields) of the game board 
        fields = []
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # convert BGR frames to gray frames

        _, frame_thresh = cv2.threshold(
            frame_gray, 170, 255, cv2.THRESH_BINARY_INV) # convert gray frames to binary frames
        cnt = self.findBiggestContour(frame_thresh) # get biggest contour (contour of gameboard)
        x,y,h,w = cv2.boundingRect(cnt)
        column = w/8 # divide with of detected gameboard into 8 column
        line = h/8 # divide height of detected gameboard into 8 rows
        points = []

        """
        determine the coordinates to get each field of the checker gameboard
        """
        for num_column in range(0,9):
            for num_line in range(0,9):
                points.append(((num_line*line)+x,(num_column*column)+y))

        for number in range(0, 71):
            if number != 8 and number != 17 and number != 26 and number != 35 and number != 44 and number != 53 and number != 62:
                field = [points[number][1], points[number+10][1], points[number][0],points[number+10][0]]
                fields.append(field)

        # calculate with the previous coordinates the centers of each field of checker gameboard and save it into arr_centroids
        for i in range (len(fields)):
            coord = (int((fields[i][2]+ fields[i][3])/2), int((fields[i][0]+fields[i][1])/2))
            arr_centroids.append(coord)

        # display the centers coordinates of each field into the frame
        for k in arr_centroids:
            frame = cv2.circle(frame, k  , 3, (0, 0, 255), -1)
        
        # use the function getPlayerCheckers() to interpretate the gameboard an get player move for checker algorithm
        self.getPlayerCheckers(arr_centroids, frame_copy)
        
        # detect pieces on the gameboard so that the user can view 
        results = self.score_frame(frame)
        frame = self.plot_boxes(results, frame)
        time.sleep(0.3)
        return frame 

    
    def runCheckers_ManuallyDetection(self, frame):
        """
        manually detection auf gameboard and game piece
        :param: frame: camera frames from appModel

        :return: frame: result frames with detection of game board and game pieces
        """
        frame_copy = frame.copy()
        arr_centroids = np.loadtxt(CENTERSCHECKERSFIELDS) # load the saved centers pixel coordinates positions of all checker gameboard fields

        arr_centroids = tuple(map(tuple, arr_centroids)) 

        if len(arr_centroids) != 64: # if the file is damaged
            self.notifyObserverViewCheckers(message="Please recalibrate the checkers board. Use the button `Calibrate Checkers Gameboard to get the center of fields`")
        
        elif len(arr_centroids) == 64: # if the file is not damaged, then send the 64 centers coordinates of all checkers fields with the RGB frame to the checker algorithm

            self.getPlayerCheckers(arr_centroids, frame_copy)
            for i in self.dictCheckers: 
                cv2.circle(frame, (int(self.dictCheckers[i][0]), int(self.dictCheckers[i][1])), 3, (0,0,255), -1)
            results = self.score_frame(frame)
            frame = self.plot_boxes(results, frame)
        time.sleep(0.3)
        return frame
    ############################################ checkers game end ############################################

    ############################################ Tic-Tac-Toe begin ############################################
    def startGameTicTT(self):
        """
        to start a new tic-tac-toe game:

        :return: None 
        """
        logger.debug("AppController tic-tac-toe game: tic-tac-toe game is starting ...")
        self.playAudio(GAMESTART)
        self.gameName = "TicTT" # set the name of the game to TicTT to send Frame only to tic-tac-toe view
        #self.notifyObserverModel()
        self.scoreTicTT = [0,0] # initialize score of payer with index 0 and Franka robot with index 1
        _thread.start_new_thread(self.doAudio, ("Welcome to Tic Tac Toe Game",)) 
        _thread.start_new_thread(self.doAudio, ("you can play now", True))
        self.notifyObserverViewTicTT(newScore= self.scoreTicTT) # send the initial score to view
        self.initGameTicTT() # initialize values to start a new tic-tac-toe game
        self.stopgameticTT = False # stop the tic tac toe game 
        self.circleData = None 
    
    def notifyObserverModel_TicTT_HomeView(self):
        """
        to notify the observer (appModel) with values:
        - cornersdataTicTT: transformation matrix for tic-tac-toe View to zoom on the game board
        - stopFPSTicTT: to hide FPS during calibration of tic-tac-toe view
        - newBrightness: to tranfert brightness values from view to model
        - stopFPSHomeView: to hide FPS during calibration of home view 
        - cornersTableData: transformation matrix for home View.
        - center_coordPixel: pixel coordinate of the tic-tac-toe field who the computer has played.
        - appName: to notify that Tic Tac Toe view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running
        - circleData: pixel coordinate of the tic-tac-toe piece outside the game board

        :return: None 
        """
        logger.debug("AppController tic-tac-toe game: notify the model about the changed values...")
        self.observerModel.updateTicTT_HomeView(cornersdataTicTT = self.cornersdataTicTT, stopFPSTicTT= self.stopFPSTicTT, newBrightness= self.brightness, stopFPSHomeView = self.stopFPSHomeView, cornersTableData = self.cornersTableData, center_coordPixel = self.center_coordPixel, appName = self.appName, circleData = self.circleData)
    
    def stopTicTT(self):
        """
        stop tic-tac-toe game, stop to send frame to the tic-tac-toe view 

        :return: None
        """
        logger.debug("AppController tic-tac-toe game: current tic-tac-toe game has been stopped!")
        self.stopgameticTT = True # set stop the tic tac toe game to true
        self.gameName = None # set the current opened windows to None
    
    def notifyObserverViewTicTT(self, newScore= None, message = None):
        """
        notify the view with the current scores and the notifications process of the tic-tac-toe game
        :param: newScore: new score of game
        :param: message: notifications message

        :return: None
        """
        logger.debug("AppController tic-tac-toe game: notify view with current scores and notifications of the game process")
        self.observerView.updateTicTTView(newScoreTicTT=newScore, message = message)
    
    def initGameTicTT(self):
        """
        initializes values to start or restart the tic-tac-toe game
        """      
        self.choose_user = True
        self.player = None
        self.computer = None
        self.initGame = False
        self.last_time = 0
        self.write_comp = False
        
        # create the game board of tic-tac-toe
        self.board = [' ' for x in range(9)]
        self.counterIndexTicTT = []
        self.stopNotifyObserverModel_TicTT_HomeView = False
        self.notifyObserverModel_TicTT_HomeView()

    def updateTicTT(self,stopFPSTicTT = False, levelTicTT = 1, cornersdataTicTT = None, appName = None):
        """
        will be used from view to notify the controller about the update informations from the tic-tac-toe view

        :return: None
        """
        self.levelTicTT = levelTicTT
        self.cornersdataTicTT = cornersdataTicTT
        self.appName = appName
        self.stopFPSTicTT = stopFPSTicTT
        self.notifyObserverModel_TicTT_HomeView()
    
    def getGameField(self, coord, frame):
        """
        cropped a frame or image with coordinate
        :param: coord: coordinates of the part of the frame or image to be cropped
        :param: frame: camera frame

        :return: crop_img: cropped image
        """
        x = coord[0]
        y = coord[1]
        w = coord[2]
        h = coord[3]
        crop_img = frame[y:y+h, x:x+w]
        return crop_img

    def preprocess_input(self, img):
        """
        Preprocess image to match model's input shape for shape detection
        :param: img: image

        :return: img.astype(np.float32) / 255: resized image 
        """
        if img is not None:
            try:
                img = cv2.resize(img, (32, 32))
                # Expand for channel_last and batch size, respectively
                img = np.expand_dims(img, axis=-1)
                img = np.expand_dims(img, axis=0)
                return img.astype(np.float32) / 255
            except:
                logger.error("empty image by preprocessing !")

    def find_shape(self, cell):
        """
        verify if shape is an X or an O on a cropped image
        :param: cell: cropped image
        
        :return: mapper[idx]: mapper value
        """
        try:
            mapper = {0: None, 1: 'X', 2: 'O'}
            cell = self.preprocess_input(cell)
            idx = np.argmax(self.modelTicTT.predict(cell))
            return mapper[idx]
        except:
            logger.error("empty image by find_shape !")

    def getShape(self, cropped):
        """
        get the predicted value on a cropped image and return it
        :param: cropped: cropped image
        
        :return: False: if no value
                 self.player: if value is `X`
        """
        if cropped is not None: 
            try:
                shape = self.find_shape(cropped)
                if shape == None:
                    return False
                elif shape == 'X':
                    self.player = "X"
                    self.computer = "O"
                    return self.player
            except:
                logger.error("empty image by getShape !")
        else:
            return False

    def getPlayer(self, points, frame):
        """
        Scans each field of the game board tic-tac-toe. 
        If a symbol (X or O) is detected, the field index 
        must be used to write the detected symbol to the 
        previously defined game board arrays.

        :param: points: 4 pixel points in a arrays to cropped a part of image frame 
        :param: frame: image frame
        
        :return: False: if no value
                 self.verifyWinner(value): after to write the pieces of player into the array. the function self.verifyWinner(value) will be used to verify if the player with the writted piece  has won't or or not or it is tie game  
        """
        self.notifyObserverViewTicTT(message="Player chooses a move !")
        gameboardIndex = 0 # to get index of the cropped image
        gameboard = np.array(self.board) # convert array into numpy array
        indexs = np.where(gameboard == ' ')[0] # get index of empy wert in array
        for field in points: 
            cropped = self.getGameField(field, frame) # croppes the frame with pixel coordinates in array points
            value = self.getShape(cropped) # get the detected symbol on the cropped image
            old_played = np.where(indexs== gameboardIndex)[0] # get the index of the arrays where the 'gameboardIndex' is present.
            if value != False and self.initGame == False and len(old_played) == 1:
                self.notifyObserverViewTicTT(message="A Move was found. Please wait 3 Seconds")
                self.last_time = int(time.time()) # get current time 
                self.initGame = True 

            # after 2 seconds write the value of the player symbol into array and verify if the player won't the game
            if value != False and int(time.time()) - self.last_time >= 3 and self.initGame == True and len(old_played) == 1:
                self.notifyObserverViewTicTT(message="Player chooses {}".format(gameboardIndex))
                self.writePosition(gameboardIndex, value)
                self.initGame = False
                self.choose_user = False
                return self.verifyWinner(value)
            
            gameboardIndex += 1
        return False

    def contoured_bbox(self, img):
        """
        Returns bounding box of contoured image
        :param: img: input image

        :return: cv2.boundingRect(sorted_cntr[-2]) 
        """
        contours, _ = cv2.findContours(img, 1, 2)
        
        if len(contours) == 0:
            return False

        sorted_cntr = sorted(contours, key=lambda cntr: cv2.contourArea(cntr))
        return cv2.boundingRect(sorted_cntr[-2])

    def get_board_template(self, thresh):
        """
        returns 3 x 3 grid
        :param: thresh: threshed image

        :return: Grid coordinates
        """
        # Find grid's center cell
        middle_center = self.contoured_bbox(thresh)
        
        center_x, center_y, width, height = middle_center

        # Useful coordinates
        left = center_x - width
        right = center_x + width
        top = center_y - height
        bottom = center_y + height

        # Middle row
        middle_left = (left, center_y, width, height)
        middle_right = (right, center_y, width, height)
        # Top row
        top_left = (left, top, width, height)
        top_center = (center_x, top, width, height)
        top_right = (right, top, width, height)
        # Bottom row
        bottom_left = (left, bottom, width, height)
        bottom_center = (center_x, bottom, width, height)
        bottom_right = (right, bottom, width, height)

        return [top_left, top_center, top_right,
                middle_left, middle_center, middle_right,
                bottom_left, bottom_center, bottom_right]

    def resultReactionWIN_LOST(self, messageObserView1, playAudioFilename, messageObserView2, incrScorePlayer = False, incrScoreRobot = False):
        """
        if the player or Franka robot win or lost this reactions will happened
        - messageObserView1: to get message in view if payer win or not and play this message with espeak
        - playAudioFilename: plays audio files to notify if player has winning the game or not 
        - messageObserView2: to notify the view that the game will start automatically after 30 seconds and to clean the gameboard. This message will be play with espeak
        - incrScorePlayer: if franka robot win, the score of franka will be increase
        - incrScoreRobot: if player win, the score of player will be increase

        :return: None
        """
        self.notifyObserverViewTicTT(message=messageObserView1)

        if incrScorePlayer == True:
            self.scoreTicTT[0] += 1
        elif incrScoreRobot == True:
            self.scoreTicTT[1] += 1

        
        self.playAudio(playAudioFilename)
        
        _thread.start_new_thread(self.doAudio, (messageObserView1,))
        self.notifyObserverViewTicTT(newScore= self.scoreTicTT)

        self.notifyObserverViewTicTT(message=messageObserView2)
        _thread.start_new_thread(self.doAudio, (messageObserView2, True))
        self.autoStartTicTT = True
        self.last_time_TicTT = int(time.time())
        
    def resultReactionTIE_GAME(self, messageObserView1, messageObserView2):
        """
        if tie game this reactions will happened
        - messageObserView1: to get tie game message in view and play this message with espeak
        - messageObserView2: to notify the view that the game will start automatically after 30 seconds and to clean the gameboard. This message will be play with espeak

        :return: None
        """
        self.notifyObserverViewTicTT(message=messageObserView1)
        _thread.start_new_thread(self.doAudio, (messageObserView1,))

        self.notifyObserverViewTicTT(message=messageObserView2)
        _thread.start_new_thread(self.doAudio, (messageObserView2, True))
        self.autoStartTicTT = True
        self.last_time_TicTT = int(time.time())

    def detectCircle(self, img):
        """
        detect circle piece for franka robot in a frame 
        :param: img: input frame

        :return: array of pixel coordinates of detected circle pieces
        """
        arr = []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Blur using 3 * 3 kernel.
        gray_blurred = cv2.blur(gray, (3, 3))

        # Apply Hough transform on the blurred image.
        detected_circles = cv2.HoughCircles(gray_blurred,
                        cv2.HOUGH_GRADIENT, 1, 20, param1 = 50,
                    param2 = 30, minRadius = 16, maxRadius = 30)

        # Draw circles that are detected.
        if detected_circles is not None:
            # Convert the circle parameters a, b and r to integers.
            detected_circles = np.uint16(np.around(detected_circles))

            for pt in detected_circles[0, :]:
                a, b, r = pt[0], pt[1], pt[2]

                # Draw the circumference of the circle.
                cv2.circle(img, (a, b), r, (0, 0, 255), 2)
                cv2.circle(img, (a, b), 3, (0, 255, 0), -1)
                
                # save pixel coordinates of detected circle pieces into a array
                arr.append((a,b))
        return arr

    def runticTT (self, frame):
        """
        To perform the detection of game field and the tic tac toe game piece and 
        verify if the game piece inside the game field or not.
        The robot grap only the pieces outside the game fields.
        :param: frame: input frame to perform the detection

        :return: frame: frame with the detected game field and game pieces
        """
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # convert BGR to GRAY
        _, frame_thresh = cv2.threshold(
            frame_gray, 170, 255, cv2.THRESH_BINARY_INV) #convert GRAY to binary images
        
        grid = self.get_board_template(frame_thresh) # get the pixels coordinates of the tic tac toe game field
        
        for i, (x, y, w, h) in enumerate(grid): # draw rectangles aver the game field with the pixels coordinates 
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 0), 2)
        
        if self.choose_user == True: # if it is the player's turn 
            result = self.getPlayer(grid, frame_thresh) # check if the player has played. If yes get the index of the field, who the player has played and write this into the array of the game field for game algorithm. At the end, check if the player has won or not
            if  result == True: # verify if the player has won 
                self.resultReactionWIN_LOST(WIN_PLAYER, GAMEWIN, GAMEBOARDCLEAN, incrScorePlayer=True) # play audio, notify the view about that the player has won the game and increment the score of player                 

            elif result == TIEGAME: # verify if tie game  
                self.resultReactionTIE_GAME(messageObserView1=TIEGAME, messageObserView2=GAMEBOARDCLEAN)  # play audio, notify the view about that the Game is tie game               
                
        elif self.choose_user == False: # if it is the computer's turn 
            self.robotAlgo(self.computer) # the computer do a move with the tic tac toe algorithm and write O's Symbol in tic tac toe array. At the end it verify if the game is tie game or if the computer has won the game 
            result = self.verifyWinner(self.computer) # get the result of the computer move
            try:
                self.printBoard(self.board) # print current array of gameboard
            except:
                print ("error with dashboard")

            if  result == True: # verify if the computer has won 
                self.resultReactionWIN_LOST(WIN_FRANKA, GAMEOVER, GAMEBOARDCLEAN, incrScoreRobot=True) # play audio, notify the view about that the computer has won the game and increment the score of computer
                
            elif result == TIEGAME: # verify if tie game  
                self.resultReactionTIE_GAME(messageObserView1=TIEGAME, messageObserView2=GAMEBOARDCLEAN) # play audio, notify the view about that the Game is tie game                
                
            self.write_comp = True # allow the computer to write its move on the gameboard virtually and allow  the sending of the coordinates that the robot needs to grab the game piece
            self.choose_user = True # after the computer has played, the can do a move

        
        arr = self.detectCircle(frame) # perform the detection of the circle pieces for the robot and save their middles coordinates into a array arr

        if self.write_comp == True:

            if self.computer == "O": # this values will be used to write the moves of player and computer into gameboard virtually 
                text = "O"
            else:
                text = "X"

            
            gameboard = np.array(self.board)
            indexs = np.where(gameboard==self.computer)[0] # get indexs of the gameboard array wo the computer has played
            for index in indexs:
                x, y, w, h = grid[index] # get the rectangle pixels coordinates of index into the grid 
                centroid = (x + int(w / 2), y + int(h / 2)) # calculate the center of this region of interest
                cv2.circle(frame, centroid, 3, (0,255,0), -1) # draw the center of the circle pieces of computer virtually inside the gameboard
                
                if text == "O":
                    cv2.circle(frame, centroid, 20, (0, 0, 255), 2) # draw the circle pieces of computer virtually inside the gameboard

            """
            The purpose of this part of the code is to check, whether a new index, 
            indicating that the computer has played, is detected or not. For this reason, 
            a helper variable has been defined (counterIndexTicTT) to store the actual array 
            having the indexes, where the computer has played.
            """
            if len(indexs) == len(self.counterIndexTicTT): # if the arrays egals the helper variable of array, then pass
                pass
            else: #if different
                arraysIndexTicTT = np.setdiff1d(indexs, self.counterIndexTicTT) # get the new index that differ on that two arrays
                
                # check the presence of the circles pieces that will be used by the robot to do their moves
                if len(arr) == 0: # if no pieces then notify the view 
                    self.notifyObserverViewCheckers(message="No circle piece has been detected. Please place the circle pieces in the view of camera so that the robot can pick it up")
                else: 

                    for i in arr: # only one piece of the detected circles pieces must be taken by the robot  
                        
                        # verify if the detected pieces is inside the gameboard 
                        # we have the coordinates of 9 rectangles of gameboard (grid). We can verify with the fonction rectContrains() if the middles coordinates of 
                        # the detected circles pieces inside the 9 rectangles of the gameboard or not. If yes, then continue  
                        if (self.rectContrains((grid[0][0],grid[0][1]), (grid[0][0] + grid[0][2], grid[0][1] + grid[0][3]), i) == True or self.rectContrains((grid[1][0],grid[1][1]), (grid[1][0] + grid[1][2], grid[1][1] + grid[1][3]), i) == True or 
                        self.rectContrains((grid[2][0],grid[2][1]), (grid[2][0] + grid[2][2], grid[2][1] + grid[2][3]), i) == True or self.rectContrains((grid[3][0],grid[3][1]), (grid[3][0] + grid[3][2], grid[3][1] + grid[3][3]), i) == True or 
                        self.rectContrains((grid[4][0],grid[4][1]), (grid[4][0] + grid[4][2], grid[4][1] + grid[4][3]), i) == True or self.rectContrains((grid[5][0],grid[5][1]), (grid[5][0] + grid[5][2], grid[5][1] + grid[5][3]), i) == True or 
                        self.rectContrains((grid[6][0],grid[6][1]), (grid[6][0] + grid[6][2], grid[6][1] + grid[6][3]), i) == True or self.rectContrains((grid[7][0],grid[7][1]), (grid[7][0] + grid[7][2], grid[7][1] + grid[7][3]), i) == True or
                        self.rectContrains((grid[8][0],grid[8][1]), (grid[8][0] + grid[8][2], grid[8][1] + grid[8][3]), i) == True):
                            continue
                        else: # if not 
                            if self.stopNotifyObserverModel_TicTT_HomeView == False: 
                                x, y, w, h = grid[arraysIndexTicTT[0]]  # get the coordinates of the new index, wo the computer has played
                                centroid = (x + int(w / 2), y + int(h / 2)) # calculate the center of this 

                                self.circleData = i # get the pixel coordinate of the circle piece outside the gameboard 

                                self.center_coordPixel = centroid 

                                self.notifyObserverModel_TicTT_HomeView() # notify the appModel with the coordinate of the index, who the camputer has played and the coordinate of the center of the circle piece outside the gameboard, that the computer can grap 
                                self.circleData = None 
                                self.center_coordPixel = None

                                break

                self.counterIndexTicTT = indexs # save the current indexs arrays in the helper array

            # if the game has done, a new game will be started in 30 seconds
            if self.autoStartTicTT == True: # 2 seconds after the game is finished, all messages to the model must be stopped.
                if int(time.time()) - self.last_time_TicTT >= 2: # 
                    self.stopNotifyObserverModel_TicTT_HomeView = True


                if int(time.time()) - self.last_time_TicTT >= 30: # 30 seconds after the game is finished, a new game can be start automatically.
                    self.initGameTicTT()
                    self.autoStartTicTT = False

        return frame
    
    def spaceIsFree(self, pos):
        """
        Checks whether a specified position in the playing field is free.
        :param: pos: specified position of the playing field to be checked.
        
        :return: None
        """
        return self.board[pos] == ' '

    def printBoard(self, board):
        """
        Draw the current state of the board.
        :param: board: Array (Tic-Tac-Toe playing field)

        :return: None
        """
        print ('   |   |' + "\t\t" + '   |   |')
        print (' ' + board[0] + ' | ' +  board[1] + ' | ' + board[2] + "\t\t" + ' ' + "0" + ' | ' +  "1" + ' | ' + "2")
        print ('   |   |' + "\t\t" + '   |   |')
        print ('-----------'+ "\t\t" + '-----------')
        print ('   |   |' + "\t\t" + '   |   |')
        print (' ' + board[3] + ' | ' +  board[4] + ' | ' + board[5] + "\t\t" +  ' ' +"3" + ' | ' +  "4" + ' | ' + "5")
        print ('   |   |' + "\t\t" + '   |   |')
        print ('-----------' + "\t\t" + '-----------')
        print ('   |   |' + "\t\t" + '   |   |')
        print (' ' + board[6] + ' | ' +  board[7] + ' | ' + board[8] + "\t\t" + ' ' +"6" + ' | ' +  "7" + ' | ' + "8")
        print ('   |   |' + "\t\t" + '   |   |')
        print ('----------------------------------------------------------------------------------------------')

    def writePosition(self, position, letter):
        """
        checks whether the specified position in the playing field is free, if so, then writes the character (X or O) in this specified position.
        :param: position: specify the position of the gameboard in which the characters must be written
        :param: letter:  X or O tic-tac-toe characters.

        :return: None
        """
        if self.spaceIsFree(position):
            self.board[position] = letter
        
    def isWinner(self, board, letter):
        """
        Checks whether the players or the computer have won if the same character occurs in the column, row or diagonal.  
        :param: board: Tic-Tac-Toe playing field
        :param: board: Characters

        :return: None
        """
        return (board[0] == letter and  board[4] == letter and board[8] == letter) or (board[2] == letter and  board[4] == letter and board[6] == letter) or (board[6] == letter and  board[7] == letter and board[8] == letter) or (board[0] == letter and  board[1] == letter and board[2] == letter) or (board[3] == letter and  board[4] == letter and board[5] == letter) or (board[0] == letter and  board[3] == letter and board[6] == letter) or (board[1] == letter and  board[4] == letter and board[7] == letter) or (board[2] == letter and  board[5] == letter and board[8] == letter)

    def isBoardFull(self, board):
        """
        Check if the board is full.
        :param: board: Tic Tac Toe playing field.

        :return: False: if the board is not full.
                 True: if the board is full.
        """
        if board.count(' ') > 1:
            return False
        else:
            return True

    def verifyWinner(self, letter):
        """
        verify if a letter (X or O) won the game
        :param: letter: X or O tic-tac-toe characters.

        :return: True: if a character has won
                 "Tie Game": if the game is tie game
                 False: if None won    
        """
        if self.isWinner(self.board, letter):
            return True

        if self.isBoardFull (self.board):
            return "Tie Game"
            
        return False

    def computerMove(self):
        """
        generates a move from the computer. The following conditions apply:
        - Checks whether the player has performed an action that can lead to the
            can cause the computer to lose the game. If so, swipe there to
            lock the player. If not, continue with step 2.

        - Check whether one of the corner squares of the playing field with the index 0, 2,
            6 or 8 is empty. If so, go there. If there is no empty bedrock
            exists, continue with step 3.

        - Check whether the difficulty level of the game is professional (1) and the center is empty (playing field with index 4). If so,
            go there. If not, continue with step 4.
        
        -  Drag it to one of the side fields with index 1, 3, 5 or 7. Once
            Step 4 is completed, there is no further action, as the remaining
            fields are only page fields.
        
        :param: None
        
        :return: move: move of computer (index of the gameboard array, wo the computer has played)
        """
        possibleMoves = [x for x, letter in enumerate(self.board) if letter == ' '] 
        move = 9

        for letter in ['O', 'X']:
            for i in possibleMoves:
                boardCopy = deepcopy(self.board)
                boardCopy[i] = letter 
                if self.isWinner (boardCopy, letter):
                    move = i
                    return move
        
        cornersOpen = []
        for i in possibleMoves:
            if i in [0, 2, 6, 8]:
                cornersOpen.append(i)
        if len(cornersOpen) > 0:
            move = self.selectRandomPosition(cornersOpen)
            return move
        
        if self.levelTicTT == 1:
            if 4 in possibleMoves:
                move = 4
                return move

        edgesOpen = []
        for i in possibleMoves:
            if i in [1, 3, 5, 7]:
                edgesOpen.append(i)
        if len(edgesOpen) > 0:
            move = self.selectRandomPosition(edgesOpen)
            return move
        return move

    def selectRandomPosition(self, li):
        """
        generates an array value of a random index of the same array.
        :param: li: specified array

        :return: li[r]: Array value of a random index of the same array.
        """
        ln = len(li)
        r = random.randint(0,ln-1)
        return li[r] 

    def robotAlgo(self, player):
        """
        - perform computer move with the O's Charachter, write the Charachter into the gameboard array
        - verify if array of gameboard is full or if the move of computer is 9
        :param: player: O's Charachter of computer
        
        :return: 'Tie Game!': if the move of computer out of range [0,1,2,3,4,5,6,7,8] or if the gameboard is full
        """
        move = self.computerMove()
        if move == 9:
            return ('Tie Game!')
        else:
            self.writePosition(move, player)
        if self.isBoardFull (self.board):
            return ('Tie Game!')
    ############################################ Tic-Tac-Toe end ############################################

    def run(self) :
        """
        run function to get the camera frames from appModel 
        and use it for the detection of game pieces or game 
        field for tic tac toe and tower of hanoi
        :param: None

        :return: None
        """
        while not self.event.is_set():
            #logger.info("Thread no stopped !")
            self.frame  = None # define a help variable to save the frame
            if not self.myResultFrameQueue_Model_Controller.empty(): # verify if the queue from appModel to appController is not empty 
                self.frame = self.myResultFrameQueue_Model_Controller.get() # get the frames from the queue 
                if (self.gameName == "TicTT" and self.stopgameticTT == False): # if the user has started the game tic tac toe  
                    try:
                        self.frame = self.runticTT(self.frame)   # the game can be started. The function runticTT use the frame for tic tac toe view from the appModel 
                    except:
                        logger.error("appController: probleme with camera frame in function run () for tic tac toe game ...")
                
                if self.appName == "tictactoe" and self.gameName != "TicTT": # if the current opened windows is tic tac toe view and the game tic tac toe has not started
                    arr = self.detectCircle(self.frame) # then detect circle pieces for the robot 
                    if len(arr) == 0: # if none circle pieces has detected, then notify the view
                        self.notifyObserverViewTicTT(message="No circle piece has been detected. Please place the circle pieces in the view of Camera so that the robot can pick it up")
                    else:
                        self.notifyObserverViewTicTT(message=None)

                if (self.gameName == "Checkers" and self.stopgameCheckers == False): # if the user has started the checker game

                    if self.use_getCenterofFields == 1: # if the user has clicked on the button "detection of the centers of the fields": "automatically" to start an automatic detection on gameboard and game pieces (the game board and game pieces can be moved in the camera area)
                        self.frame = self.runCheckers_AutomaticallyDetection(self.frame)
                    else: # if the user has clicked on the button "detection of the centers of the fields": "manually" to start an manually detection on gameboard and game pieces (the game board and game pieces can only take a posion in the camera area. After the position of gameboard is defined, then the user can click on button "Calibrate Checkers Gameboard to get the centers of fields" to get the centers of fields)
                        self.frame = self.runCheckers_ManuallyDetection(self.frame)
     
                            
                if self.getCenterofFieldsCheckers == False: # if the user click on "Calibrate Checkers Gameboard to get the centers of fields", getCenterofFieldsCheckers is set to False and the detection of the centers of fields beginn.
                    self.frame = self.getCentersFields(self.frame)
                
                if self.getCenterofFieldsCheckers == True: # if the user click on "Get Centers now", the current detected centers of fields were be saved into './data/centers_Checkers_Fields.txt'
                    np.savetxt(CENTERSCHECKERSFIELDS, self.arr_centroids, fmt='%i')
                    self.notifyObserverViewCheckers(message="the centers of fields has been saved ...")
                
            if not self.myResultFrameQueue_Controller_Model.full(): # send the result frame into a queue to the appModel
                self.myResultFrameQueue_Controller_Model.put(self.frame)
            
            time.sleep(0.1)      
        logger.debug("AppController: thread stopped, exit ...")
        exit()