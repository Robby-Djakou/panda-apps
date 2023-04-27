#
### appModel.py 
# implements model component of MVC architecture of Franka Emika Games
# implement the algorithm to convert pixel coordinates into panda-coordinates
# connected with the camera and the panda-robot 
# generate camera-frames and send it over queue to the controller to perform detection.
# send robot coordinates over frankx to panda-robot

import threading  # Parent Class
import logging
import time
import cv2                          # to perform opencv transformation and debugging
import videoStreamer
from config import *
import queue
from argparse import ArgumentParser
import math
from re import L
from time import sleep
# from frankx import Affine, JointMotion, LinearMotion, Robot, LinearRelativeMotion, Waypoint, Kinematics, NullSpaceHandling, WaypointMotion # to use panda-robot
import _thread 

# create logger
logger = logging.getLogger('appModel.py') 
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create log file
ch = logging.FileHandler('logs/appModel.log', mode='w')

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

class AppModel(threading.Thread):
    def __init__(self, event, resultFrameProducer, myResultFrameQueue_Model_Controller, myResultFrameQueue_Controller_Model, myResultFrameQueue_Model_View, lockForimshow):
        threading.Thread.__init__(self)  
        """
        class to implement model component of Franka Emika Games app
        :param: event 
        :param: resultFrameProducer
        :param: myResultFrameQueue_Model_Controller
        :param: myResultFrameQueue_Model_Controller 
        :param: myResultFrameQueue_Controller_Model
        :param: lockForimshow
        
        :return: create the model Component
        """
        self.event = event
        self.lockForimshow = lockForimshow # debug opencv
        self.resultFrameProducer = resultFrameProducer # send frames over the queue to view (for homeview and tower of hanoi)
        self.myResultFrameQueue_Model_Controller = myResultFrameQueue_Model_Controller  # send frames over the queue to controller (for tic tac toe and checker)
        self.myResultFrameQueue_Controller_Model = myResultFrameQueue_Controller_Model # get frames from controller
        self.myResultFrameQueue_Model_View = myResultFrameQueue_Model_View # send frame over the queue to view (for tic tac toe and checker)
        
        # determine current and previous time to calcule the fps for the camera frames
        self.newFrameTime= 0
        self.previousFrameTime= 0

        # to get camera frames and adjust brightness of frames
        self.camStreamer= videoStreamer.VideoStreamer(self.event)
        self.camStreamer.start() 
        self.stopFPSHomeView = False # stop fps during the calibration of camera view in homeview
        self.cornersTableData = None # opencv matrix of 4 points on the white table of panda-robot
        self.appName = None # to notify the appModel  to send the camera frame to the currrent openend view
        
        ################# Tower of Hanoi 
        self.counter_TOH = 0  # number of moves
        self.positionFrom = None # start tower 
        self.positionTo = None # destination tower

        ################# Tic Tac Toe 
        self.stopFPSTicTT = False # stop fps during the calibration of camera view in tic tac toe view
        self.Z_object_TicTT = 0.027430 # panda z-coordinate of the tic tac toe circles piece, to grab this on a plane surface

        ################# Checker
        self.stopFPSCheckers = False # stop fps during the calibration of camera view in checker view
        self.Z_object_Checkers = 0.023 # panda z-coordinate of hanoi piece, to grab this on a plane surface
        
        ################# Panda-Robot
        # to connect with pandas
        """self.HOST = "141.28.57.193"  # Standard loopback interface address (localhost)
        self.PORT = 65440  # Port to listen on (non-privileged ports are > 1023)
        self.parser = ArgumentParser()
        self.parser.add_argument('--host', default='192.168.100.100', help='FCI IP of the robot')
        self.args = self.parser.parse_args()

        # Connect to the robot
        self.robot = Robot(self.args.host)
        self.robot.set_default_behavior()
        self.robot.recover_from_errors()
        self.gripper = self.robot.get_gripper() # connect to gripper

        # configure force and speed of gripper to maximum
        self.gripper.gripper_force = 1.0 
        self.gripper.gripper_speed = 1.0
        
        ################# configure the maximum values of velocity, acceleration and jerk
        self.robot.set_dynamic_rel(0.2)
        # self.robot.velocity_rel = 0.3
        # self.robot.acceleration_rel = 0.3
        # self.robot.jerk_rel = 0.3

        ################# initialize the panda-robot to the home pose
        self.robot.move(JointMotion(HOME_JOINT))"""
        
    
    def pixelToXY_Robot(self, pixel_centerx, pixel_centery, X_ROBOT_SHIFFTING = -0.015, Y_ROBOT_SHIFFTING = 0):
        """in this function we will convert the pixel data of the objects 
        detected by the camera into robot coordinates so that the robot can 
        grab the object
        
        :param :pixel_centerx x-coordinate of the center of the object detected by the camera.
        :param :pixel_centery y-coordinate of the center of the object detected by the camera.

        :return x,y-coordinate of the center of the detected object from  the robot base
        """
        CM_TO_PIXEL = TABLE_WIDTH/640 # pixel to CM       
        
        # convert the pixel coordinates of the center of the detected object to cm 
        centerx = pixel_centerx * CM_TO_PIXEL
        centery = pixel_centery * CM_TO_PIXEL

        # Coordinates of the object in the camera reference
        CAMERA_REFERENCE = np.array([[centerx],
                                [centery],
                                [0.0],
                                [1]])
                                
        # Create the homogeneous transformation matrix from robot base to camera base
        HOMOGEN_TRANSFORMATION = np.concatenate((ROTATION_ROBOT_CAMERA, TRANSLATION_VECTOR), axis=1) 

        # Coordinates of the object in Robot reference 
        ROBOT_REFERENCE = HOMOGEN_TRANSFORMATION @ CAMERA_REFERENCE 

        # due to the fact that the coordinates in the 
        # robot reference are in meter, it will be necessary 
        # to convert the received coordinates from centimeter to meter 
        robotX = ROBOT_REFERENCE[0][0]/100 + X_ROBOT_SHIFFTING
        robotY = ROBOT_REFERENCE[1][0]/100 + Y_ROBOT_SHIFFTING

        return robotX, robotY


    def updateTicTT_HomeView(self, cornersdataTicTT = None, newBrightness= 0, stopFPSHomeView = False, stopFPSTicTT = False, cornersTableData = None, center_coordPixel = None, appName = None, circleData = None):
        """
        update values using by the appController to notify the appModel.
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
        self.appName = appName

        """if self.appName == "tictactoe": 
            self.robot.move(JointMotion(HOME_JOINT)) # if the user open the view of tic tac toe, than the roboter take the home pose"""


        self.cornersdataTicTT = cornersdataTicTT
        self.cornersTableData = cornersTableData

        self.camStreamer.setBrightness(newBrightness) # set the Brightness to VideoStreamer
        self.stopFPSHomeView = stopFPSHomeView
        self.stopFPSTicTT = stopFPSTicTT

        if not circleData is None and not center_coordPixel is None: # if circle pieces for the panda-roboter detected and centers coordinates of tic tac toe gameboard fields, where the robot played is available   
            center_coordPixel_new = (center_coordPixel[0], center_coordPixel[1]) 
            #self.game_TicTT(center_coordPixel_new, circleData) # use the function game_TicTT to convert pixel into panda-koordinate and send its to panda-robot 
            
    def game_TicTT(self, center_coordPixel, circleData):
        """
        convert the pixel coordinates into panda-coordinates and send the computer move to panda-robot
        :param: center_coordPixel: center pixels coordinates of the field, where the robot played. 
        :param: circleData: detected circle game pieces for the robot so that the computer can grab

        :return: None
        """
        self.robot.move(JointMotion(HOME_JOINT)) # Panda-robot take home pose
        self.gripper.open() # Panda-robot open gripper
        
        robotX1, robotY1 = self.pixelToXY_Robot(circleData[0], circleData[1], X_ROBOT_SHIFFTING=-0.025) # convert pixel coordinate of detected circle piece to panda coordinate
        self.robot.move(LinearMotion(Affine(robotX1, robotY1,  0.01556))) # panda-robot use the result coordinate to go on the position of the circle piece
        self.gripper.clamp() # Panda-robot close gripper to grab the circle piece
        self.robot.move(LinearMotion(Affine(robotX1, robotY1, 0.1))) # panda-robot goes up one centimetre
        robotX2, robotY2 = self.pixelToXY_Robot(center_coordPixel[0], center_coordPixel[1]) # convert the destination pixel coordinate to panda-coordinate
        self.robot.move(LinearMotion(Affine(robotX2, robotY2, 0.025))) # panda-robot use the result  coordinate to go on the position of the destination field of tic tac toe gameboard
        self.gripper.open() # open gripper to drop the circle piece
        self.gripper.release() # release gripper
        self.robot.move(JointMotion(HOME_JOINT)) # go to home position 

    def update_TOH(self, dataTOH = [], stateTOH = [], counter_TOH = 0, appName = None):
        """
        update values using by the appController to notify the appModel.
        - counter_TOH: Anzahl von Zügen (Bewegungen) bis zu Ergebnisse
        - dataTOH: content the enter information (from Pegs, to Pegs, temporyPegs) of the user, the Pixel coordinate of the 3 towers and the disc number
        - stateTOH: the different movements and positions involved. 
        - appName: to notify that Tower of hanoi view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running

        :return: None
        """
        self.appName = appName
        """if self.appName == "menu_or_toh": 
            self.robot.move(JointMotion(HOME_JOINT))"""

        self.dataTOH = dataTOH 
        self.stateTOH = stateTOH
        self.counter_TOH = counter_TOH
        #_thread.start_new_thread(self.game_TOH, ()) # create a new thread to use the function game_TOH()

    def game_TOH(self):
        """
        convert the pixel coordinates into panda-coordinates and send the computer move to panda-robot
        :param: None

        :return: None
        """
        self.robot.move(JointMotion(HOME_JOINT)) # Panda-robot take home pose
        
        count = 1 # value to help the panda-robot at the end of the possibles moves to take the home position
        count_Z1, count_Z2, count_Z3 = 0, 0, 0 # Initialize the three tower at the beginning with no disc (0)
        
        for i in self.stateTOH:   
            if i[1] == 0:   # if the start tower is 0 (A) where the discs have been placed.
                self.positionFrom = self.dataTOH[4] # get value of tower A, where the discs have been placed. 
                if count_Z1 == 0 and count_Z2 == 0 and count_Z3 == 0: # if tower A is  at the beginning of the game the start tower, the other 3 tower must be empty
                    count_Z1 = self.dataTOH[0] # tower A get the total number of the disc at the biginning
                
                Z_Base = 0.019343 # panda z-coordinate of the tower of hanoi piece, to grab this on a plane surface
                Z_ = None # current z-coordinate of the above disc on a tower


                # get the z-coordinate of the first disc above on tower A
                for j in range (count_Z1-1):
                    Z_Base+=0.009
                Z_ = Z_Base
                
                # after take the first disc on tower A, tower A must decrement the current number of disc
                # and the corresponded self.positionTo the count_ZX must increment
                if count_Z1 != 0 or count_Z2 != 0 or count_Z3 != 0:
                    if count_Z1 == -1:
                        count_Z1 = 0
                    else:
                        count_Z1-=1

                
            if i[1] == 1: # if the start tower is 1 (B) where the discs have been placed.
                self.positionFrom = self.dataTOH[5]  # get value of tower B, where the discs have been placed. 
                
                if count_Z1 == 0 and count_Z2 == 0 and count_Z3 == 0: # if tower B is  at the beginning of the game the start tower, the other 3 tower must be empty
                    count_Z2 = self.dataTOH[0] # tower B get the total number of the disc at the biginning
                
                Z_Base = 0.019343 # panda z-coordinate of the tower of hanoi piece, to grab this on a plane surface
                
                # get the z-coordinate of the first disc above on tower B
                for j in range (count_Z2-1):  
                    Z_Base+=0.009
                Z_ = Z_Base

                # after take this disc on tower B, tower B must decrement the current number of disc
                # and the corresponded self.positionTo the count_ZX must increment
                if count_Z1 != 0 or count_Z2 != 0 or count_Z3 != 0:
                    if count_Z2 == -1:
                        count_Z2 = 0
                    else:
                        count_Z2-=1

            if i[1] == 2: # if the start tower is 2 (C) where the discs have been placed.
                self.positionFrom = self.dataTOH[6]  # get value of tower C, where the discs have been placed. 
                
                if count_Z1 == 0 and count_Z2 == 0 and count_Z3 == 0: # if tower C is  at the beginning of the game the start tower, the other 3 tower must be empty
                    count_Z3 = self.dataTOH[0] # tower C get the total number of the disc at the biginning
                
                Z_Base = 0.019343 # panda z-coordinate of the tower of hanoi piece, to grab this on a plane surface

                # get the z-coordinate of the first disc above on tower C
                for j in range (count_Z3-1):
                    Z_Base+=0.009
                Z_ = Z_Base
                
                # after take this disc on tower C, tower C must decrement the current number of disc
                # and the corresponded self.positionTo the count_ZX must increment
                if count_Z1 != 0 or count_Z2 != 0 or count_Z3 != 0:
                    if count_Z3 == -1:
                        count_Z3 = 0
                    else:
                        count_Z3-=1

            if i[2] == 0: # if the cible tower is 0 (A) where the discs will be placed.
                self.positionTo = self.dataTOH[4] # pixel coordinate of destination tower if tower A
                count_Z1 += 1 # if a disc is posed in Tower A, the number of the disc into this tower will increment

            if i[2] == 1: # if the cible tower is 1 (B) where the discs will be placed.
                self.positionTo = self.dataTOH[5] # pixel coordinate of destination tower if tower B
                count_Z2 += 1 # if a disc is posed in Tower B, the number of the disc into this tower will increment

            if i[2] == 2: # if the cible tower is 2 (C) where the discs will be placed.
                self.positionTo = self.dataTOH[6] # pixel coordinate of destination tower if tower C
                count_Z3 += 1 # if a disc is posed in tower C, the number of the disc into this tower will increment


            self.gripper.open() # open gripper
            coordinatesFrom = self.pixelToXY_Robot(self.positionFrom[0], self.positionFrom[1], X_ROBOT_SHIFFTING=0) # convert start pixel position of tower into panda coordinate 
            self.robot.move(LinearMotion(Affine(coordinatesFrom[0], coordinatesFrom[1], 0.1)))  # panda-robot use the result  coordinate to go on the start position

            self.robot.move(LinearMotion(Affine(coordinatesFrom[0], coordinatesFrom[1], Z_))) # panda-robot use the current z calculated coordinate to grab the disc at the same position
            self.gripper.clamp() 
            self.robot.move(LinearMotion(Affine(coordinatesFrom[0], coordinatesFrom[1], 0.1)))  # panda-robot goes up one centimetre
            
            coordinatesTo = self.pixelToXY_Robot(self.positionTo[0], self.positionTo[1], X_ROBOT_SHIFFTING=0) # convert destination pixel position of tower into panda coordinate 
            self.robot.move(LinearMotion(Affine(coordinatesTo[0], coordinatesTo[1], Z_+0.02))) # panda-robot use the current z calculated coordinate to drop the disc 2 cm higher
            self.gripper.open() #open gripper
            self.robot.move(LinearMotion(Affine(coordinatesTo[0], coordinatesTo[1], 0.1))) 
            
            if count == self.counter_TOH:
                self.robot.move(JointMotion(HOME_JOINT)) # take home pose if total move is egal to count
            count+=1


    def update_Checkers(self, cornersdataCheckers=None, appName = None, stopFPSCheckers = False):
        """
        update values using by the appController to notify the appModel.
        - cornersdataCheckers: transformation matrix for Checkers View to zoom on game board
        - stopFPSCheckers: to hide FPS during calibration
        - appName: to notify that Tic Tac Toe view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running

        :return: None
        """
        #if self.appName == "checkers":
        #    self.robot.move(JointMotion(HOME_JOINT))
        self.stopFPSCheckers = stopFPSCheckers
        self.appName = appName
        self.cornersdataCheckers = cornersdataCheckers


    def update_Checkers_Robot(self, xy_coord_From, xy_coord_To, viaPiece):
        """
        update values using by the appController to notify the appModel.
        - xy_coord_From: The pixel coordinates of the piece to be moved
        - xy_coord_To: The pixel coordinates of the position where the piece is to be moved.
        - viaPiece: if available, the player's pieces that have been jumped
        
        :return: None
        """
        self.game_Checkers (xy_coord_From, xy_coord_To, xy_coord_via=viaPiece) # use the function game_Checkers to convert pixel into panda-koordinate and send its to panda-robot 


    def game_Checkers(self, xy_coord_From, xy_coord_To, xy_coord_via = []):
        """
        convert pixel into panda-koordinate and send its to panda-robot 
        :param: xy_coord_From: start position of checker piece
        :param: xy_coord_To: destination position of checker piece
        :param: xy_coord_via: player piece, that has been jumby 

        :return: None
        """
        self.robot.move(JointMotion(HOME_JOINT)) # Home position
        self.gripper.move(0.06) # open gripper 6 mm
        robotFromX, robotFromY = self.pixelToXY_Robot(xy_coord_From[0], xy_coord_From[1]) # convert pixel start position of the moved piece into panda coordinate 
        robotToX, robotToY = self.pixelToXY_Robot(xy_coord_To[0], xy_coord_To[1])  # convert pixel destination position of the moved piece into panda coordinate 
        
        self.robot.move(LinearMotion(Affine(robotFromX, robotFromY, 0.1)))
        self.robot.move(LinearMotion(Affine(robotFromX, robotFromY, self.Z_object_Checkers))) # panda robot move to this position to take the checker piece
        self.gripper.clamp()
        self.robot.move(LinearMotion(Affine(robotFromX, robotFromY, 0.1)))
        self.robot.move(LinearMotion(Affine(robotToX, robotToY, 0.1)))
        self.robot.move(LinearMotion(Affine(robotToX, robotToY, self.Z_object_Checkers))) # panda robot move to this position to drop the gripped checker piece
        self.gripper.move(0.06)
        self.robot.move(LinearMotion(Affine(robotToX, robotToY, 0.1)))


        if len(xy_coord_via) != 0: # if a player has been jumbed by computer piece 
            for i in xy_coord_via:
                robotViaX, robotViaY = self.pixelToXY_Robot(i[0], i[1])
                self.gripper.move(0.06)
                self.robot.move(LinearMotion(Affine(robotViaX, robotViaY, 0.1)))
                
                self.robot.move(LinearMotion(Affine(robotViaX, robotViaY, self.Z_object_Checkers))) # go to the position of player piece
                self.gripper.clamp() # grab player piece
                self.robot.move(LinearMotion(Affine(robotViaX, robotViaY, 0.1)))
                self.robot.move(LinearMotion(Affine(0.119622, -0.340037, 0.1))) # drop player piece
                self.gripper.open()

        
        self.robot.move(JointMotion(HOME_JOINT)) # go to home pose
        self.gripper.release()


    def run(self):
        """
        run function to get the camera frames and transfert it to appController and appView, perform the opencv transformation 
        :param: None

        :return: None
        """
        while not self.event.is_set():
            #logger.info("Thread no stopped !")
            self.frame = self.camStreamer.read() # get frames from VideoStreamer
            if (self.frame is None or self.frame.size == 0):
                time.sleep(1.1)
                continue 
            else :  # if frames available
                if (self.cornersTableData is not None):
                    self.frame = cv2.warpPerspective(self.frame, self.cornersTableData,(WIDTH, HEIGHT)) # opencv transformation of the 4 points on the robot table             

                if (FLIPHORIZONTAL == True): # flip horizontal if activated
                    self.frame= cv2.flip(self.frame, 1)

                self.frame_Game =   self.frame.copy() 
                self.frame_Game_final = None # result frame for tic tac toe and checkers view

                if self.appName == "tictactoe": # if the user has opened the tic tac toe window (view) 
                    self.newFrameTime = time.time() # get current time
                    if not self.myResultFrameQueue_Model_Controller.full():
                        self.myResultFrameQueue_Model_Controller.put(self.frame_Game) # if queue empty, then send the frames to the controller for tic tac toe algorithm
                    
                    if not self.myResultFrameQueue_Controller_Model.empty():
                        self.frame_Game_final = self.myResultFrameQueue_Controller_Model.get() # if queue not empty, then get the result frames from the controller 

                    if OPENCV_DEBUG_TIC_TAC_TOE == True: # for debugging tic tac toe camera view
                        self.lockForimshow.acquire()
                        cv2.imshow("Tic Tac Toe", self.frame_Game_final)
                        key= cv2.waitKey(1)
                        self.lockForimshow.release()
                        if (key == ord("q") or key == 27):
                            logger.info("AppModel: ESC or q, exit...")
                            self.event.set()  # kill other threads

                    if (self.frame_Game_final is  None or self.frame_Game_final.size == 0):
                        pass
                    else:
                        if self.cornersdataTicTT is not None:
                            self.frame_Game_final = cv2.warpPerspective(self.frame_Game_final, self.cornersdataTicTT,(WIDTH, HEIGHT)) # opencv transformation for zoom 
                        
                    if (SHOWFPS == True and self.stopFPSTicTT == False):
                        outText = "FPS: {:.1f}".format(1/(self.newFrameTime - self.previousFrameTime))
                        cv2.putText(self.frame_Game_final, outText, (WIDTH-170, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 40, 255), 2) # display fps in camera view
                    self.previousFrameTime = time.time()
                                        
                    if not self.myResultFrameQueue_Model_View.full():
                        if self.frame_Game_final is None:
                            pass
                        else:
                            self.myResultFrameQueue_Model_View.put(self.frame_Game_final) # send the result frames to the appView
                
                elif self.appName == "checkers": # if the user has opened the checkers window (view) 
                    self.newFrameTime = time.time()
                    #self.frame_Game = cv2.flip(self.frame_Game, -1)
                    if not self.myResultFrameQueue_Model_Controller.full():
                        self.myResultFrameQueue_Model_Controller.put(self.frame_Game)
                    
                    if not self.myResultFrameQueue_Controller_Model.empty():
                        self.frame_Game_final = self.myResultFrameQueue_Controller_Model.get()

                    if OPENCV_DEBUG_CHECKERS == True:
                        self.lockForimshow.acquire()
                        cv2.imshow("Checkers", self.frame_Game_final)
                        key= cv2.waitKey(1)
                        self.lockForimshow.release()
                        if (key == ord("q") or key == 27):
                            logger.info("AppModel: ESC or q, exit...")
                            self.event.set()  # kill other threads

                    if (self.frame_Game_final is  None or self.frame_Game_final.size == 0):
                        pass
                    else:
                        if self.cornersdataCheckers is not None:
                            self.frame_Game_final = cv2.warpPerspective(self.frame_Game_final, self.cornersdataCheckers,(WIDTH, HEIGHT)) 

                    if (SHOWFPS == True and self.stopFPSCheckers == False):
                        outText = "FPS: {:.1f}".format(1/(self.newFrameTime - self.previousFrameTime))
                        cv2.putText(self.frame_Game_final, outText, (WIDTH-170, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 40, 255), 2)
                    self.previousFrameTime = time.time()
                    if not self.myResultFrameQueue_Model_View.full():
                        if self.frame_Game_final is None:
                            pass
                        else:         
                            self.myResultFrameQueue_Model_View.put(self.frame_Game_final)

                elif self.appName == "menu_or_toh": # if the user has opened the homeview or tower of hanoi window (view) 
                    self.newFrameTime = time.time()

                    if OPENCV_DEBUG_HOME_TOH == True:
                        self.lockForimshow.acquire()
                        cv2.imshow("Home and Tower of Hanoi", self.frame)
                        key= cv2.waitKey(1)
                        self.lockForimshow.release()
                        if (key == ord("q") or key == 27):
                            logger.info("AppModel: ESC or q, exit...")
                            self.event.set()  # kill other threads

                    if (SHOWFPS == True and self.stopFPSHomeView == False):
                        outText = "FPS: {:.1f}".format(1/(self.newFrameTime - self.previousFrameTime))
                        cv2.putText(self.frame, outText, (WIDTH-170, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 40, 255), 2)
                    self.previousFrameTime = time.time()

                    if not self.resultFrameProducer.full():
                        self.resultFrameProducer.put(self.frame) # send frame to appView for tower of hanoi and homeview
                time.sleep(0.1)
        logger.debug("AppModel: thread stopped, exit ...")
        exit()