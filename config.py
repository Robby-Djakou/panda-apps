# python config-parameters of Franka Emika Games App

import numpy as np 

# Capture Device
CAPTUREDEVICE = "/dev/video4"   # capture Camera Index for Linux
#CAPTUREDEVICE = 4  # capture Camera Index for windows
WIDTH = 640 # image camera width for OpenCV
HEIGHT =  480   # image camera height for OpenCV
BRIGHTNESSMIN = 0   # minimum camera brightness
DEFAULTBRIGHTNESS = 128 # Default camera Brigthness, if the file data/brightness.txt is not available      
BRIGHTNESSMAX = 255 # maximum camera brightness
FPS = 30    # fps for Camera
FLIPHORIZONTAL = False # flip image if the camera has changed the orientation


# View parameters and calibration parameters
BRIGHTNESSFILE = "./data/brightness.txt"    # to save current BRIGHTNESS of View
CORNERSTABLE_DATA = "./data/corners_ROBOT_table.txt"    # to save the current 4 marked points on the Table for calibration
CORNERSTicTT = "./data/corners_TicTT_gameboard.txt" # to save the 4 points for warpPerspective with opencv (the goal of this option is to zoom the view of Tic Tac Toe gameboard)
CORNERSCHECKERS = "./data/corners_Checkers_gameboard.txt"   # to save the 4 points for warpPerspective with opencv (the goal of this option is to zoom on the view of Checkers gameboard)
CENTERSCHECKERSFIELDS = "./data/centers_Checkers_Fields.txt" # to save the 64 pixels centers coordinates of fields of the gameboard checkers
SAVE_STATE_CHECKERS_GAME = "data/continue_save_state_Checkers.npy" # to save the array of the current state of checkers game

# show or hide FPS during the calibration
SHOWFPS = True


# sound parameters for Games
BEEPFILE = "./sounds/beep.wav"
BEEPFILE_ERROR = "./sounds/pling.wav"
GAMESTART = "./sounds/game_start.wav"
GAMEOVER = "./sounds/game_over.wav"
GAMEWIN = "./sounds/game_win.wav"


# Control Audio Speak ouput
SPEAKAUDIO = True


# espeak message 
WIN_FRANKA = "Franka won this game"
WIN_PLAYER = "You won this game"
TIEGAME = "Tie Game"
GAMEBOARDCLEAN = "Please clean the Gameboard. A new Game will start in 30 seconds !"
PlAYER_PLAY = "Player is playing"
FRANKA_PLAY = "Franka Emika Robot is playing!"


MAXLEN = 1  # max length of queues 


# Data for the conversion of pixels to centimeters (CM)
TABLE_WIDTH = 69  # width of the table in CM for the calculation of the calibration. 

# Rotation matrix from robot base to camera base
ROTATION_ROBOT_CAMERA = np.array([[0, -1, 0],
                                  [-1, 0, 0],
                                  [0, 0, -1]])

# coordinate of the left top marked point on the table to the robot base
TRANSLATION_VECTOR = np.array([[74.6116],
                                [32.3218], 
                                [0.0]])

# Robot Joint Parameters 
# Home position for the Robot
HOME_JOINT = [-1.620304166268884, 0.019030814074330386, 0.030113897909023402, -1.7129097922308403, -0.02432454986687791, 1.7265477380022152, 0.7217509774690869]


# model filename 
MODEL_TIC_TAC_TOE = "./data/tic-tac-toe_Model/model.h5" # to detect tic tac toe game pieces 
MODEL_CHECKERS = "./yolov5/runs/train/exp/weights/best.pt" # to detect checkers game pieces 


DIRECTORY_MODEL_CHECKERS = "./yolov5" # home directory for checkers-Game model  

# the height and width of the area in the view in which the camera frames must be displayed.
VIEWWIDTH = 640 # width
VIEWHEIGHT =  480   # height

# to Debug  camera frames for Home and tower of hanoi view
OPENCV_DEBUG_HOME_TOH = False

# to Debug camera frames for tic tac toe view
OPENCV_DEBUG_TIC_TAC_TOE = False

# to Debug camera frames for checkers view 
OPENCV_DEBUG_CHECKERS = False