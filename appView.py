#
### appView.py 
# implements View component of MVC architecture of Franka Emika Games
#
#
import numpy as np
import time
import cv2 
from pygame import mixer    # to play audio file for Games 
import os                   # for checking brightness file
from config import *
import logging

# GUI 
import tkinter
import PIL.Image, PIL.ImageTk
from tkinter import CENTER, IntVar, Tk, BOTH, Radiobutton, Button, Scale, Toplevel, RIDGE
from tkinter.ttk import Frame, Label,Entry
import threading

# create logger
logger = logging.getLogger('appView.py') 
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create log file
ch = logging.FileHandler('logs/appView.log', mode='w')

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


# Appview run in a Mainloop Thread
class AppView(threading.Thread):            
    def __init__(self, event, resultFrameConsumer, resultFrameConsumer_Game, getCORNERSTABLE, getCORNERSTicTT, getCORNERSCHECKERS,  observer):
        """
        class to implement Home View component of Franka Emika Games app
        :param: event 
        :param: resultFrameConsumer
        :param: resultFrameConsumer_Game
        :param: getCORNERSTABLE
        :param: getCORNERSTicTT
        :param: getCORNERSCHECKERS
        :param: observer
        
        :return: create the Home View Component with a TKinter GUI
        """
        logger.debug("AppView: Home View init...")
        self.resultFrameConsumer = resultFrameConsumer # reads frames from Consumer-Queue for Homeview and tower of hanoi View
        self.resultFrameConsumer_Game = resultFrameConsumer_Game # reads frames from Consumer-Queue for tic Tac Toe and Checkers
        self.getCORNERSTABLE = getCORNERSTABLE # no matrix available, then start a new calibration, to get the 4 points on robot table 
        self.getCORNERSTicTT = getCORNERSTicTT # no matrix available, then start a new calibration, to get 4 points, to zoom the tic tac toe gameboard
        self.getCORNERSCHECKERS = getCORNERSCHECKERS # # no matrix available, then start a new calibration, to get 4 points, to zoom the checkers gameboard
        self.event= event 
        self.observer= observer # appView acts as Observable, observer (appController)   
        self.observer.registerObserverView(self) # register appView as Observer of appController (observable) to get score of Checkers and Tic Tac Toe      
        
        ############ HomeView #################
        self.appName = "menu_or_toh"    # initialize self.appName to notify the appModel, to send the camera frame only to Queue for Home View, not for tic tac toe or checkers View
        self.cornersTable = [] # hold 4 pixel coordinates points on the table for calibration matrix


        ############ Tower of Hanoi ###########
        self.dataTOH = [] #content the enter information by the user (from Pegs, to Pegs, temporyPegs), the Pixel coordinate of the 3 towers and the disc number
        self.storageTOH = None # the Pixel coordinate of the 3 top of pegs
        self.stopselectTower = True # help to start or stop the process to get the pixel coordinate of top of pegs
        self.counttower = [] # save the pixel coordinate of top of pegs
        self.scoreCheckers = [0,0] # get current score (player, Franka Roboter) from appController for checkers

        
        ############ Tic Tac Toe ###############    
        self.scoreTicTT = [0,0] # get current score (player, Franka Roboter) from appController for Tic Tac Toe
        

        mixer.init() # initialize Mixer to play Sound Game filename               
        
        # set saved brightness from "./data/brightness.txt" or default brightness (128)
        self.useDefaultBrightness = not os.path.isfile(BRIGHTNESSFILE)
        if self.useDefaultBrightness :
            self.brightness= DEFAULTBRIGHTNESS
        else :
            self.brightness = np.loadtxt(BRIGHTNESSFILE, dtype=int)

        logger.debug("AppView: Home View brightness= %s", self.brightness)
        
        ############## Main TK-Window ###################
        self.window = Tk() # initialize Tkinter root view
        self.window.title('Franka Emika Games') # set title of root or main view
        self.window.bind("<KeyPress>", self.onKeyPressHomeView) # bind main view with keypress event (:q to exit the view, :d to delete points during the calibration)
        self.window.bind("<Escape>", self.onEscape) # bind main view with keypress event escape to exit the view

        # Canvas to contain a video 
        self.tkVideoFrame = Frame(self.window, relief=RIDGE, borderwidth=10)
        self.tkVideoFrame.pack(fill=BOTH, expand=True)

        # Make a canvas that will suit the video source size mentioned above. 
        self.canvas = tkinter.Canvas(self.tkVideoFrame, width=VIEWWIDTH,height=VIEWHEIGHT)
        self.canvas.pack()

        # construct a frame for the first instruction content
        self.textLabel1 = Frame(self.window, relief=RIDGE, borderwidth=1)
        self.textLabel1.pack(fill=BOTH, expand=True)
        self.labelText = Label(self.textLabel1,background='orange', anchor=CENTER, text="Please select corners or black points of robot table with the button `Calibrate Camera` and select one game !", font=('verdana', 14, 'bold'))
        self.labelText.pack(ipadx=20, ipady=10, expand=True, fill='both', side='top')

        # construct a frame for the second instruction content
        self.textLabel2 = Frame(self.window, relief=RIDGE, borderwidth=1)
        self.textLabel2.pack(fill=BOTH, expand=True)
        self.labelText2 = Label(self.textLabel2,background='orange', anchor=CENTER, text="If the Position of the Camera since restart of application hasn't moved, you don't need to use `Calibrate Camera`", font=('verdana', 14, 'bold'))
        self.labelText2.pack(ipadx=20, ipady=10, expand=True, fill='both', side='top')

        # construct a frame to control the brightness and create 3 Buttons
        self.tkBtnFrame = Frame(self.window, relief=RIDGE, borderwidth=1)
        self.tkBtnFrame.pack(fill=BOTH, expand=True)

        self.slider = Scale(self.tkBtnFrame, from_=BRIGHTNESSMIN,
                            to=BRIGHTNESSMAX, command= self.onSliderChanged,
                            label="Brightness", bd=3, orient='horizontal')
        self.slider.pack(ipadx=20, ipady=10, fill='both', side='top', expand=True)

        # set the value of DEFAULTBRIGHTNESS or BRIGHTNESSFILE
        self.slider.set(self.brightness)
        
        # create 3 buttons to start 3 Views for the Game Tic Tac Toe, Tower of Hanoi or Checkers
        self.btnTicTacToe = Button(self.tkBtnFrame, text="Tic Tac Toe Game", font=('verdana', 18, 'bold'), command=self.tictacToe)
        self.btnTowerofHanoi = Button(self.tkBtnFrame, text="Tower of Hanoi", font=('verdana', 18, 'bold'), command=self.towerofHanoi)
        self.btnchessGame = Button(self.tkBtnFrame, text="Checkers Game", font=('verdana', 18, 'bold'), command=self.checkers)
        
        self.btnTicTacToe.pack(ipadx=5, ipady=15, fill='both', side='left', expand=True)
        self.btnTowerofHanoi.pack(ipadx=5, ipady=15, fill='both', side='left', expand=True)
        self.btnchessGame.pack(ipadx=5, ipady=15, fill='both', side='right', expand=True)

        # construct a frame to create the button exit for the home view 
        self.tkBtn1Frame = Frame(self.window, relief=RIDGE, borderwidth=1)
        self.tkBtn1Frame.pack(fill=BOTH, expand=True)

        self.btnQuit = Button(self.tkBtn1Frame, text="Exit", activebackground = "red", font=('verdana', 18, 'bold'), width=50, borderwidth=3, command=self.exit)
        self.btnQuit.pack(ipadx=10, ipady=10, fill='both', side='bottom',expand=True)

        # construct a frame to create the button `calibrate Camera`
        self.tkBtn2Frame = Frame(self.window, relief=RIDGE, borderwidth=1)
        self.tkBtn2Frame.pack(fill=BOTH, expand=True)

        self.btnCalibrate = Button(self.tkBtn2Frame, text="Calibrate Camera", borderwidth=3, command=self.findConersTable)
        self.btnCalibrate.pack(ipadx=10, ipady=10, fill='both', anchor=tkinter.CENTER, expand=True)
        
        # The updateTK() function will been called automatically after 40 milliseconds. 
        self.delay = 40
        self.updateTK()

        # load the matrix from "./data/corners_ROBOT_table.txt"
        # if matrix not available, start new calibration
        if not self.getCORNERSTABLE:
            logger.info("Matrix for Home View available")
            self.allPointsCORNERS = np.loadtxt(CORNERSTABLE_DATA, dtype=float)
        else:
            logger.info("Matrix for Home View not available")
            self.allPointsCORNERS  = None    

        # The update function of tic tac toe, tower of hanoi and checkers will been called automatically after 100 milliseconds for View of the Games.
        self.delay_games_windows = 100

        # notify Obeserver
        self.notifyObserverHomeView()



    def onSliderChanged(self, event):
        """
        to get the current brightness and notify the controller with this value
        :param: event: value of brightness

        :return: None
        """
        self.brightness= self.slider.get()
        logger.debug("AppView: brightness= %s", self.brightness)
        self.notifyObserverHomeView()



    def playAudio(self, audiofilename):
        """
        play the audiofilename of the Games
        :param: audiofilename: soundfile Game 

        :return: None
        """
        alert = mixer.Sound(audiofilename)
        logger.debug("AppView: audiofilename= {} will been played".format(audiofilename))
        alert.play()


    
    def exit(self):
        """
        exit from AppView and destroy mainloop, save the current brightness value into file "./data/brightness.txt" and set the event of Threading to True
        to notify and destroy the thread of the others Threads
        """
        logger.debug("AppView: thread stopped, exit ...")
        #logger.debug("AppView: exit...")
        np.savetxt(BRIGHTNESSFILE, [self.brightness], fmt='%d')
        self.playAudio(BEEPFILE)
        self.event.set()       
        time.sleep(0.2)
        self.window.destroy()
    


    def onMouseClickHomeView(self, mouseClick):
        """
        save the points during the calibration in the array self.cornersTable
        :param: mouseClick: click event

        :return: None
        """
        logger.debug("AppView onMouseClickHomeView to get pixel coordinate")
        if (len(self.cornersTable) < 4):
            self.playAudio(BEEPFILE)
            xCoord = mouseClick.x
            yCoord = mouseClick.y
            self.cornersTable.append([xCoord, yCoord])

    
    def onKeyPressHomeView(self, key):
        """
         Called when a key is pressed in the checkers Home View windows (root windows)
         :param: key: key-event

         :return: None
        """
        logger.debug("AppView Home view: keyPressed %s", key.char)
        if ( key.char == 'q') :# to exit from view
            self.onEscape(key)
        elif (key.char == 'd' and len (self.cornersTable)> 0) : # to delete points during the calibration for zoom
            self.cornersTable.pop()
        elif (key.char == 'd' and len (self.cornersTable) == 0) : # to cancel the calibration process when it has already been started
            self.canvas.unbind("<Button 1>")        # unregister Click-Handler
            self.btnCalibrate.config(font= ('verdana', 12, 'normal'), fg='black', text="Calibrate Camera") # set the text of calibration button to origin
            self.getCORNERSTABLE =  False
            self.allPointsCORNERS = self.allPointsCORNERS_New # the copy matrix will been reuse, when the calibration will been canceled
            self.notifyObserverHomeView() # notify observer



    def notifyObserverHomeView(self):
        """
        to notify the observer (appController) with values:
        - brightness
        - stopFPS: during the calibration FPS will been hided
        - cornersTableData: matrix for Home View Calibration
        - appName: to notify that Home View is launch. The Goal is to notify the appModel for it to send the camera frame to the current view running

        :return: None 
        """
        logger.debug("AppView Home view: notifyObserverHomeView")
        self.observer.updateHomeView(brightness=self.brightness,  stopFPSHomeView = self.getCORNERSTABLE, cornersTableData = self.allPointsCORNERS, appName = self.appName)


    
    def findConersTable(self):
        """
        starts new Calibration and ask user for 4 corner points

        :return: None
        """
        logger.debug("AppView: calibrate Home view")
        if not self.getCORNERSTABLE:       
            self.playAudio(BEEPFILE)
            self.getCORNERSTABLE= True
            self.allPointsCORNERS_New = self.allPointsCORNERS # copy the current matrix, if the user cancel the calibration, the old matrix can been reused
            self.allPointsCORNERS =  None # initialize the value to get the new matrix 
            self.notifyObserverHomeView() # notify the observer without a matrix to send the frame to the appView without any cv2 transformation
        
        self.btnCalibrate.config(font= ('verdana', 12, 'bold'), fg='red',
                                text= "Click on the 4 Corners of the Table: <NW>, NE, SW, SE, or 'd' to delete last Corner or 'd' to stop the calibration")
        self.canvas.bind("<Button 1>",self.onMouseClickHomeView) # bind click event
        return
    


    def drawCornersAndLine(self):
        """
        draws Line to help the user to find the point on the table. 
        The Goal is to draw a point when the user select a click on a point on table for calibration

        :return: None
        """
        #logger.debug("AppView: drawCornersAndLine Home View")
        if (self.getCORNERSTABLE):         
            w = WIDTH
            h = HEIGHT
            i = 0
            while (i <=480):
                cv2.line(self.frame, (0,i), (w,i), (0,0,0), 1)
                i += 10
    
        for (x, y) in self.cornersTable:
            cv2.circle(self.frame, (x, y), 10, (0, 255, 255), -1)



    def onEscape(self, event):  
        """
        catch ESC-key and exit from appView

        :return: None
        """    
        self.exit()



    def updateTK(self):
        """
        update function for Home View

        :return: None
        """
        if self.event.is_set():
            self.exit()
    
        if (self.getCORNERSTABLE and len(self.cornersTable)== 0 ): # to start new calibration
            self.findConersTable()

        if not self.resultFrameConsumer.empty():
            self.frame = self.resultFrameConsumer.get()
            if (not self.frame.size == 0):
                #logger.debug("AppView: camera frame available for Canvas in Home View")
                self.drawCornersAndLine()  # indicate (x,y)-Coordinates for Calibration
                self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
                self.photo = PIL.ImageTk.PhotoImage(master= self.canvas, image=PIL.Image.fromarray(self.frame))
                self.canvas.create_image(0, 0, image=self.photo, anchor=tkinter.NW) # draw camera frame on canvas
        
        # update the message on calibration button
        if (len(self.cornersTable) == 1):
            self.btnCalibrate.config(text="Click on the 4 Corners of the Table: NW, <NE>, SW, SE or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersTable) == 2):
            self.btnCalibrate.config(text="Click on the 4 Corners of the Table: NW, NE, <SW>, SE or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersTable) == 3):
            self.btnCalibrate.config(text="Click on the 4 Corners of the Table: NW, NE, SW, <SE> or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersTable) == 4):
            # if the 4 points has been defined, then start the perspective transform of opencv 
            self.canvas.unbind("<Button 1>")        # unregister Click-Handler
            self.btnCalibrate.config(font= ('verdana', 12, 'normal'), fg='black', text="Calibrate Camera")
            self.getCORNERSTABLE =  False
            pts1 = np.float32(self.cornersTable)
            pts2 = np.float32([[0, 0], [WIDTH, 0],
                               [0, HEIGHT], [WIDTH, HEIGHT]])
        
            self.allPointsCORNERS = cv2.getPerspectiveTransform(pts1, pts2)
            np.savetxt(CORNERSTABLE_DATA, self.allPointsCORNERS, fmt='%f') # save the current matrix after the opencv transformation
            not self.notifyObserverHomeView() 
            self.cornersTable=[] # empty the cornersTable to reuse it for a new calibration
            logger.debug("AppView: calibration in Home View is finish")
        self.window.after(self.delay, self.updateTK) # update the Tkinter GUI after 40 milliseconds


    ######################################### Tic Tac Toe begin ##################################################
    def tictacToe(self):
        """
        initialize view of Tic Tac Toe Game

        :return: create the Tic Tac Toe View Component with a TKinter GUI from Home View
        """
        logger.debug("AppView: Tic Tac Toe View init...")
        self.playAudio(BEEPFILE) # play beep file by click
        self.window.withdraw() # hide Home View 
        self.appName = "tictactoe"  # initialize self.appName to notify the appModel, to send the camera frame only to Queue for tic tac toe View
        self.windowTicTT = Toplevel(self.window) # initialize Tic Tac Toe View from Home View
        
        self.windowTicTT.title('Tic Tac Toe Game') # set title of view 
        self.windowTicTT.bind("<KeyPress>", self.onKeyPressTicTT) # bind tic tac toe view with keypress event (:q to exit the view, :d to delete points during the calibration)
        self.windowTicTT.bind("<Escape>", self.onEscape)# bind tic tac toe view with keypress event escape to exit the view
        
        # construct a frame to content the title of the Game
        tFrameTitle = Frame(self.windowTicTT, relief=RIDGE, borderwidth=1)
        tFrameTitle.pack(fill=BOTH)

        headTicTT = Label(tFrameTitle, anchor=CENTER, text='Welcome to Tic Tac Toe Game', font=('verdana', 20, 'bold'))
        headTicTT.pack(fill='both', side='top', ipadx=20, ipady=20)

        # Canvas to contain a video 
        tkVideoFrameTicTT = Frame(self.windowTicTT, relief=RIDGE, borderwidth=10)
        tkVideoFrameTicTT.pack(fill=BOTH,  expand=True)
        self.canvasTicTT = tkinter.Canvas(tkVideoFrameTicTT, width=VIEWWIDTH,height=VIEWHEIGHT)
        self.canvasTicTT.pack()

        # construct a frame to content a empty place to show the notification of game, if available
        tFrame0 = Frame(self.windowTicTT,  relief=RIDGE, borderwidth=1)
        tFrame0.pack(fill=BOTH, expand=True)

        self.notificationLabelTicTT = Label(tFrame0, font=('verdana', 14, 'bold'), anchor=CENTER)
        self.notificationLabelTicTT.pack(ipadx=10, ipady=10, expand=True, fill='both', side='top')

        # construct a frame to hold and center inner Frame
        tkScoreFrameOut = Frame(self.windowTicTT, borderwidth=0)
        tkScoreFrameOut.pack(fill=BOTH, expand=False)

        # construct a frame to hold Labels and Scores in Grid layout
        tkScoreFrame = Frame(tkScoreFrameOut, borderwidth=0)
        tkScoreFrame.grid(row=0, column=0, sticky="")
        tkScoreFrameOut.grid_rowconfigure(0, weight=1)
        tkScoreFrameOut.grid_columnconfigure(0, weight=1)

        # construct a frame to display player and Robot scores
        labelPlayer = Label(tkScoreFrame, text='Player', font=('verdana', 24, 'bold'))
        labelPlayer.grid(row=0, column=0)
        labelRobot = Label(tkScoreFrame, text='Franka Roboter', font=('verdana', 24, 'bold'))
        labelRobot.grid(row=0, column=2)
        self.labelPlayerScoreTicTT = Label(tkScoreFrame, text='-', font=('verdana', 48, 'bold'))
        self.labelPlayerScoreTicTT.grid(row=1, column=0, padx=100)
        labelPlayerSeparator = Label(tkScoreFrame, text=':', font=('verdana', 48, 'bold'))
        labelPlayerSeparator.grid(row=1, column=1, padx=20)
        self.labelRobotScoreTicTT = Label(tkScoreFrame, text='-', font=('verdana', 48, 'bold'))
        self.labelRobotScoreTicTT.grid(row=1, column=2, padx=100)

        # construct a frame to hold Radio buttons for "level" of game Tic Tac Toe
        tkBtnFrame = Frame(self.windowTicTT, relief=RIDGE, borderwidth=1)
        tkBtnFrame.pack(fill=BOTH, expand=True)
        
        self.levelTicTT= IntVar()
        self.levelTicTT.set(1)          # start level with "professional"
        labelLevel = Label(tkBtnFrame, text='Level:', font=('verdana', 16, 'bold'))
        labelLevel.pack(padx=20, ipady=10, expand=True, fill='both', side='left')

        # radiobutton for beginner
        radioBtnLevel1 = Radiobutton(tkBtnFrame, variable=self.levelTicTT, value=0,
                                          indicatoron = 0, borderwidth=3, font=('verdana', 12, 'bold'), text="Beginner", width=10 , command=self.notifyObserverTicTT)
        radioBtnLevel1.pack(ipadx=10, ipady=10, expand=True, fill='both', side='left')
        
        # radiobutton for professional
        radioBtnLevel2 = Radiobutton(tkBtnFrame, variable=self.levelTicTT, value=1,
                                          indicatoron = 0, borderwidth=3, font=('verdana', 12, 'bold'), text="Professional", width=10 , command=self.notifyObserverTicTT)
        radioBtnLevel2.pack(ipadx=10, ipady=10, expand=True, fill='both', side='left')

        logger.debug("AppView: Tic Tac Toe Game level {}".format(self.levelTicTT.get()))

        # construct a frame to create the button "New Game" to start the game tic tac toe
        tkBtn1Frame = Frame(self.windowTicTT, relief=RIDGE, borderwidth=1)
        tkBtn1Frame.pack(fill=BOTH, expand=True)

        self.btnStartTicTT = Button(tkBtn1Frame, text="New Game", font=('verdana', 18, 'bold'), activebackground = "green", borderwidth=3, command=self.newGameTicTT)
        self.btnStartTicTT.pack(ipadx=5, ipady=10, fill='both', side='left', expand=True)      

        # construct a frame to create the button exit for the tic tac toe view 
        tFrameExit = Frame(self.windowTicTT,  relief=RIDGE, borderwidth=1)
        tFrameExit.pack(fill=BOTH)
        btnQuitTicTT = Button(tFrameExit, text="Exit", activebackground = "red", font=('verdana', 18, 'bold'), width=50, borderwidth=3, command=self.exitTicTT)
        btnQuitTicTT.pack(ipadx=10, ipady=10, fill='both', side='bottom',expand=True)

        # calibrate button to zoom on tic tac toe gameboard
        tkBtn2Frame = Frame(self.windowTicTT, relief=RIDGE, borderwidth=1)
        tkBtn2Frame.pack(fill=BOTH, expand=True)
        self.btnCalibrateTicTT = Button(tkBtn2Frame, text="Calibrate Tic Tac Toe Gameboard for Zoom", width=50, borderwidth=3, command=self.findConersTicTT)
        self.btnCalibrateTicTT.pack(ipadx=10, ipady=10, fill='both', anchor=tkinter.CENTER, expand=True)


        self.cornersTicTT = [] # hold 4 pixel coordinates points for calibration matrix (zoom on tic tac toe gameboard)
        self.allPoints = None  # to store calibration matrix

        # load the matrix from "./data/corners_TicTT_gameboard.txt"
        # if matrix not available, start new calibration
        if not self.getCORNERSTicTT:
            logger.info("Matrix for Tic Tac Toe View available")
            self.allPoints = np.loadtxt(CORNERSTicTT, dtype=float)
        else:
            logger.info("Matrix for Tic Tac Toe View not available")
            self.allPoints = None


        # notify observer
        self.notifyObserverTicTT()

        # update function of tic tac toe View
        self.updateTKTicTT()



    def exitTicTT(self):
        """
        exit from tic tac toe View and restore (show) the Home view (root view), destroy tic tac toe view and notify the appModel to stop the frame for tic tac toe View, 
        but now to send frame only for Home View

        :return: None
        """
        logger.debug("AppView: Tic Tac Toe View exit...")
        self.playAudio(BEEPFILE)
        time.sleep(0.2)
        self.windowTicTT.destroy()
        self.window.deiconify()
        self.observer.stopTicTT()
        self.appName = "menu_or_toh"
        self.notifyObserverTicTT()



    def onKeyPressTicTT(self, key):
        """
         Called when a key is pressed in the Tic Tac Toe View windows
         :param: key: key-event

         :return: None
        """
        logger.debug("AppView Tic Tac Toe view: keyPressed %s", key.char)
        if ( key.char == 'q') :
            self.onEscape(key)
        elif (key.char == 'd' and len (self.cornersTicTT)> 0) :
            self.cornersTicTT.pop()
        elif (key.char == 'd' and len (self.cornersTicTT)== 0) :
            self.canvasTicTT.unbind("<Button 1>")        
            self.btnCalibrateTicTT.config(font= ('verdana', 12, 'normal'), fg='black', text="Calibrate Tic Tac Toe Gameboard")
            self.getCORNERSTicTT = False
            self.allPoints = self.allPoints_new
            self.notifyObserverTicTT()



    def notifyObserverTicTT(self):
        """
        to notify the observer (appController) with values:
        - stopFPSTicTT: to hide FPS during calibration
        - levelTicTT: level of tic tac toe Games (0 beginner or 1 for professional)
        - cornersdataTicTT: matrix for Tic Tac Toe View
        - appName: to notify that Tic Tac Toe view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running

        :return: None 
        """
        logger.debug("AppView Tic Tac Toe view: notifyObserverTicTT")
        self.observer.updateTicTT(stopFPSTicTT = self.getCORNERSTicTT, levelTicTT = self.levelTicTT.get(), cornersdataTicTT = self.allPoints, appName = self.appName)



    def newGameTicTT(self):
        """
        notify the observer appController to start a new game and set the text of start button to restart

        :return: None
        """
        logger.debug("AppView Tic Tac Toe view: Start new Game Tic Tac Toe")
        self.playAudio(BEEPFILE)
        self.observer.startGameTicTT()
        self.btnStartTicTT.config(text= "Restart")



    def findConersTicTT(self):
        """
        starts new Calibration and ask user for 4 corner points

        :return: None
        """
        logger.debug("AppView: calibrate Tic Tac Toe view")
        if not self.getCORNERSTicTT:       
            self.playAudio(BEEPFILE)
            self.getCORNERSTicTT= True
            self.allPoints_new = self.allPoints
            self.allPoints =  None
            self.notifyObserverTicTT()
        
        self.btnCalibrateTicTT.config(font= ('verdana', 12, 'bold'), fg='red',
                                text= "Click on 4 Corners of Tic Tac Toe Gameboard: <NW>, NE, SW, SE, or 'd' to delete last Corner or 'd' to stop the calibration")
        self.canvasTicTT.bind("<Button 1>",self.onMouseClickTicTT)
        return



    def drawCornersAndGridTicTT(self):
        """
        draws grid to help the user to draw points for a new transformation matrix (calibration). 

        :return: None
        """
        #logger.debug("AppView: drawCornersAndGrid for Tic Tac Toe View")
        if (self.getCORNERSTicTT):         
            w = WIDTH
            h = HEIGHT
            cv2.line(self.frameTicTT, (0,0), (w,h), (0,0,0), 1)
            cv2.line(self.frameTicTT, (0,h), (w,0), (0,0,0), 1)
            steps = 10
            deltaX = w // (steps * 2)
            deltaY = h // (steps * 2)
            xmin = 0
            ymin = 0
            xmax = w
            ymax = h
            for i in range (1, steps) :
                xmin+= deltaX
                ymin+= deltaY
                xmax-= deltaX
                ymax-= deltaY
                cv2.rectangle( self.frameTicTT, (xmin, ymin), (xmax, ymax), (0,0,0), 1)
        for (x, y) in self.cornersTicTT:
            cv2.circle(self.frameTicTT, (x, y), 10, (0, 255, 255), -1)

    


    def onMouseClickTicTT(self, mouseClick):
        """
        save the points during the calibration in the array self.cornersTicTT
        :param: mouseClick: click event

        :return: None
        """
        logger.debug("AppView onMouseClickTicTT to get pixel coordinate")
        if (len(self.cornersTicTT) < 4):
            self.playAudio(BEEPFILE)
            xCoord = mouseClick.x
            yCoord = mouseClick.y
            self.cornersTicTT.append([xCoord, yCoord])


    

    def updateTKTicTT(self):
        """
        update function for Tic Tac Toe View

        :return: None
        """
        if self.event.is_set():
            logger.debug("appView: Tic-Tac-Toe thread stopped, exit ...")
            self.exit()
        
        if (self.getCORNERSTicTT and len(self.cornersTicTT)== 0 ):# to start new calibration
            self.findConersTicTT()
        if not self.resultFrameConsumer_Game.empty():
            self.frameTicTT = self.resultFrameConsumer_Game.get()
            if (not self.frameTicTT.size == 0):
                #logger.debug("AppView: camera frame available for Canvas in Tic Tac Toe View")
                self.drawCornersAndGridTicTT()  # indicate (x,y)-Coords for Calibration
                self.frameTicTT = cv2.cvtColor(self.frameTicTT, cv2.COLOR_BGR2RGB)
                self.photoTicTT = PIL.ImageTk.PhotoImage(master= self.canvasTicTT, image=PIL.Image.fromarray(self.frameTicTT))
                self.canvasTicTT.create_image(0, 0, image=self.photoTicTT, anchor=tkinter.NW)# draw camera frame on canvas
        
        if (len(self.cornersTicTT) == 1):
            self.btnCalibrateTicTT.config(text="Click on 4 Corners of Tic Tac Toe Gameboard: NW, <NE>, SW, SE or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersTicTT) == 2):
            self.btnCalibrateTicTT.config(text="Click on 4 Corners of Tic Tac Toe Gameboard: NW, NE, <SW>, SE or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersTicTT) == 3):
            self.btnCalibrateTicTT.config(text="Click on 4 Corners of Tic Tac Toe Gameboard: NW, NE, SW, <SE> or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersTicTT) == 4):
            # if the 4 points has been defined, then start the perspective transform of opencv 
            self.canvasTicTT.unbind("<Button 1>")        # unregister Click-Handler
            self.btnCalibrateTicTT.config(font= ('verdana', 12, 'normal'), fg='black', text="Calibrate Tic Tac Toe Gameboard")
            self.getCORNERSTicTT =  False
            pts1 = np.float32(self.cornersTicTT)
            pts2 = np.float32([[0, 0], [WIDTH, 0],
                               [0, HEIGHT], [WIDTH, HEIGHT]])
        
            self.allPoints = cv2.getPerspectiveTransform(pts1, pts2)
            np.savetxt(CORNERSTicTT, self.allPoints, fmt='%f') # save the current matrix after the opencv transformation
            not self.notifyObserverTicTT()
            self.cornersTicTT=[] # empty the cornersTable to reuse it for a new calibration
            logger.debug("AppView: calibration in Tic Tac Toe View is finish")
        self.windowTicTT.after(self.delay, self.updateTKTicTT) # update the Tkinter GUI after 100 milliseconds
    ######################################### Tic Tac Toe end ##################################################


    

    ####################################### checkers game begin ###########################################
    def checkers(self):
        """
        initialize view of checkers Game

        :return: create checkers View Component with a TKinter GUI from Home View
        """
        logger.debug("AppView: checkers View init...")
        self.playAudio(BEEPFILE)# play beep file by click
        self.window.withdraw() # hide Home View 
        self.appName = "checkers" # initialize self.appName to notify the appModel, to send the camera frame only to Queue for checkers View
        self.windowCheckers = Toplevel(self.window) # initialize checkers View from Home View
        self.windowCheckers.title('Checkers Game')# set title of view 
        self.windowCheckers.bind("<KeyPress>", self.onKeyPressCheckers)# bind checkers view with keypress event (:q to exit the view, :d to delete points during the calibration)
        self.windowCheckers.bind("<Escape>", self.onEscape)# bind checkers view with keypress event escape to exit the view
        
        # construct a frame to content the title of the Game
        tFrameTitle = Frame(self.windowCheckers, relief=RIDGE, borderwidth=1)
        tFrameTitle.pack(fill=BOTH)

        headCheckers = Label(tFrameTitle, anchor=CENTER, text='Welcome to Checkers Game', font=('verdana', 20, 'bold'))
        headCheckers.pack(fill='both', side='top', ipadx=20, ipady=20)

        # variable to help to start or stop the functionality to get the center of 64 fields of checkers board  
        self.getcalibrateCentersFieldsCheckers = False
        self.getCenterofFieldsCheckers = None

        # Canvas to contain a video 
        tkVideoFrameCheckers = Frame(self.windowCheckers, relief=RIDGE, borderwidth=10)
        tkVideoFrameCheckers.pack(fill=BOTH,  expand=True)
        self.canvasCheckers = tkinter.Canvas(tkVideoFrameCheckers, width=VIEWWIDTH,height=VIEWHEIGHT)
        self.canvasCheckers.pack()

        # construct a frame to content a empty place to show the notification of game, if available
        tFrame0 = Frame(self.windowCheckers,  relief=RIDGE, borderwidth=1)
        tFrame0.pack(fill=BOTH, expand=True)
        self.notificationLabelCheckers = Label(tFrame0, font=('verdana', 14, 'bold'), anchor=CENTER)
        self.notificationLabelCheckers.pack(ipadx=10, ipady=10, expand=True, fill='both', side='top')


        # construct a frame to hold and center inner Frame
        tkScoreFrameOut = Frame(self.windowCheckers, borderwidth=0)
        tkScoreFrameOut.pack(fill=BOTH, expand=False)

        # construct a frame to hold Labels and Scores in Grid layout
        tkScoreFrame = Frame(tkScoreFrameOut, borderwidth=0)
        tkScoreFrame.grid(row=0, column=0, sticky="")
        tkScoreFrameOut.grid_rowconfigure(0, weight=1)
        tkScoreFrameOut.grid_columnconfigure(0, weight=1)

        # construct a frame to display player and Robot scores
        labelPlayer = Label(tkScoreFrame, text='Player', font=('verdana', 24, 'bold'))
        labelPlayer.grid(row=0, column=0)
        labelRobot = Label(tkScoreFrame, text='Franka Roboter', font=('verdana', 24, 'bold'))
        labelRobot.grid(row=0, column=2)
        self.labelPlayerScoreCheckers = Label(tkScoreFrame, text='-', font=('verdana', 48, 'bold'))
        self.labelPlayerScoreCheckers.grid(row=1, column=0, padx=100)
        labelPlayerSeparator = Label(tkScoreFrame, text=':', font=('verdana', 48, 'bold'))
        labelPlayerSeparator.grid(row=1, column=1, padx=20)
        self.labelRobotScoreCheckers = Label(tkScoreFrame, text='-', font=('verdana', 48, 'bold'))
        self.labelRobotScoreCheckers.grid(row=1, column=2, padx=100)


        # construct a frame to hold Radio buttons for "level" of checkers game
        tkBtnFrame = Frame(self.windowCheckers, relief=RIDGE, borderwidth=1)
        tkBtnFrame.pack(fill=BOTH, expand=True)
        
        self.levelCheckers= IntVar()

        

        self.levelCheckers.set(1)          # start level with "professional"
        
        
        labelLevel = Label(tkBtnFrame, text='Level:', font=('verdana', 16, 'bold'))
        labelLevel.pack(padx=20, ipady=10, expand=True, fill='both', side='left')
        
        # radiobutton to disable mandatory jump
        radioBtnLevel1 = Radiobutton(tkBtnFrame, variable=self.levelCheckers, value=0,
                                          indicatoron = 0, borderwidth=3, font=('verdana', 12, 'bold'), text="disable mandatory jump", width=10 , command=self.notifyObserverCheckers)
        radioBtnLevel1.pack(ipadx=10, ipady=10, expand=True, fill='both', side='left')
        
        # radiobutton to enable mandatory jump
        radioBtnLevel2 = Radiobutton(tkBtnFrame, variable=self.levelCheckers, value=1,
                                          indicatoron = 0, borderwidth=3, font=('verdana', 12, 'bold'), text="enable mandatory jump", width=10 , command=self.notifyObserverCheckers)
        radioBtnLevel2.pack(ipadx=10, ipady=10, expand=True, fill='both', side='left')
        
        logger.debug("AppView: checkers Game level {}".format(self.levelCheckers.get()))

        
        # configure the button to get the centers of fields from Checkers gameboard
        tkBtnFrame_get_center = Frame(self.windowCheckers, relief=RIDGE, borderwidth=1)
        tkBtnFrame_get_center.pack(fill=BOTH, expand=True)

        self.useButton_get_center = IntVar()
        self.useButton_get_center.set(1)          
        
        
        labe_useButton_get_center = Label(tkBtnFrame_get_center, text='Detection of the centers of the fields:', font=('verdana', 16, 'bold'))
        labe_useButton_get_center.pack(padx=20, ipady=10, expand=True, fill='both', side='left')
        
        # radiobutton to deactivate automaticaly detection of centers of the fields 
        radioBtnEnableDetection = Radiobutton(tkBtnFrame_get_center, variable=self.useButton_get_center, value=0,
                                          indicatoron = 0, borderwidth=3, font=('verdana', 12, 'bold'), text="manually", width=10 , command=self.notifyObserverCheckers)
        radioBtnEnableDetection.pack(ipadx=10, ipady=10, expand=True, fill='both', side='left')
        
        # radiobutton to activate automaticaly detection of centers of the fields
        radioBtnDisableDetection = Radiobutton(tkBtnFrame_get_center, variable=self.useButton_get_center, value=1,
                                          indicatoron = 0, borderwidth=3, font=('verdana', 12, 'bold'), text="automaticaly", width=10 , command=self.notifyObserverCheckers)
        radioBtnDisableDetection.pack(ipadx=10, ipady=10, expand=True, fill='both', side='left')

        logger.debug("Detection of the centers of the fields {}".format(self.useButton_get_center.get()))






        # construct a frame to create the button "New Game" to start the game checkers
        tkBtn1Frame = Frame(self.windowCheckers, relief=RIDGE, borderwidth=1)
        tkBtn1Frame.pack(fill=BOTH, expand=True)

        self.btnStartCheckers = Button(tkBtn1Frame, text="New Game", font=('verdana', 18, 'bold'), activebackground = "green", borderwidth=3, command=self.newGameCheckers)
        self.btnStartCheckers.pack(ipadx=5, ipady=10, fill='both', side='left', expand=True)  

        tkBtnpause_continueFrame = Frame(self.windowCheckers, relief=RIDGE, borderwidth=1)
        tkBtnpause_continueFrame.pack(fill=BOTH, expand=True)

        self.btncontinueCheckers = Button(tkBtnpause_continueFrame, text="Continue the last saved checkers game status", font=('verdana', 18, 'bold'), activebackground = "green", borderwidth=3, command=self.continueGameCheckers)
        self.btncontinueCheckers.pack(ipadx=5, ipady=10, fill='both', side='right', expand=True)   

        self.btnpauseCheckers = Button(tkBtnpause_continueFrame, text="Save current checkers game status", font=('verdana', 18, 'bold'), activebackground = "#ff8000", borderwidth=3, command=self.saveStateGameCheckers)
        self.btnpauseCheckers.pack(ipadx=5, ipady=10, fill='both', side='right', expand=True)   

        # construct a frame to create the button exit for the checkers view
        tFrameExit = Frame(self.windowCheckers,  relief=RIDGE, borderwidth=1)
        tFrameExit.pack(fill=BOTH)
        btnQuitCkeckers = Button(tFrameExit, text="Exit", activebackground = "red", font=('verdana', 18, 'bold'), width=50, borderwidth=3, command=self.exitCheckers)
        btnQuitCkeckers.pack(ipadx=10, ipady=10, fill='both', side='bottom',expand=True)

        # calibrate button to zoom on checkers gameboard
        tkBtn2Frame = Frame(self.windowCheckers, relief=RIDGE, borderwidth=1)
        tkBtn2Frame.pack(fill=BOTH, expand=True)

        self.btnCalibrateCheckers = Button(tkBtn2Frame, text="Calibrate Checkers Gameboard for Zoom", width=50, borderwidth=3, command=self.findConersCheckers)
        self.btnCalibrateCheckers.pack(ipadx=10, ipady=10, fill='both',side='left', anchor=tkinter.CENTER, expand=True)
        
        # Button to get the center of the 64 fields of checkers gameboard and save this in a file
        self.btnCalibrateCheckers2 = Button(tkBtn2Frame, text="Calibrate Checkers Gameboard to get the centers of fields", width=50, borderwidth=3 , command=self.findCenterFieldsCheckers)
        self.btnCalibrateCheckers2.pack(ipadx=10, ipady=10, fill='both',side='right', anchor=tkinter.CENTER, expand=True)

        self.cornersCheckers = [] # hold 4 pixel coordinates points for calibration matrix 
        self.allPointsCheckers = None # to store calibration matrix

        # load the matrix from "./data/corners_Checkers_gameboard.txt"
        # if matrix not available, start new calibration
        if not self.getCORNERSCHECKERS:
            logger.info("Matrix for checkers available (zoom)")
            self.allPointsCheckers = np.loadtxt(CORNERSCHECKERS, dtype=float)
        else:
            logger.info("Matrix for checkers not available (zoom)")
            self.allPointsCheckers = None


        # notify observer
        self.notifyObserverCheckers()

        # update function of checkers View
        self.updateTKCheckers()

    
    def onKeyPressCheckers(self, key):
        """
         Called when a key is pressed in the checkers window
         :param: key: key-event

         :return: None
        """

        logging.error("AppView checkers: keyPressed %s", key.char)
        if ( key.char == 'q') : # to exit from view
            self.onEscape(key) 
        elif (key.char == 'd' and len (self.cornersCheckers)> 0) : # to delete points during the calibration for zoom
            self.cornersCheckers.pop() 
        elif (key.char == 'd' and len (self.cornersCheckers)== 0) : # to cancel the calibration process when it has already been started
            self.canvasCheckers.unbind("<Button 1>")        # unregister Click-Handler
            self.btnCalibrateCheckers.config(font= ('verdana', 12, 'normal'), fg='black', text="Calibrate Checkers Gameboard") # set the text of calibration button to origin
            self.getCORNERSCHECKERS = False  
            self.allPointsCheckers = self.allPointsCheckers_new # the copy matrix will been reuse, when the calibration will been canceled
            self.notifyObserverCheckers() # notify observer 
        


    def exitCheckers(self):
        """
        exit from checkers View and restore (show) the Home view (root view), destroy checkers view and notify the appModel to stop the frame for checkers View, 
        but now to send frame only for Home View

        :return: None
        """
        logger.debug("AppView: checkers View exit...")
        self.playAudio(BEEPFILE)
        time.sleep(0.2)
        self.windowCheckers.destroy()
        self.window.deiconify()
        self.observer.stopCheckers()
        self.appName = "menu_or_toh"
        self.notifyObserverCheckers()

    


    def notifyObserverCheckers(self):
        """
        to notify the observer (appController) with values:
        - stopFPSCheckers: to hide FPS during calibration
        - levelCheckers: level of checkers Games (0 beginner or 1 for professional)
        - cornersdataCheckers: matrix for checkers View
        - appName: to notify that checkers view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running
        - getCenterofFieldsCheckers: to get the centers of fields of checkers Gameboard
        - use_getCenterofFields: to notify that the user want to use the option or not to get the centers of fields of checkers Gameboard 
       
        :return: None 
        """
        logger.debug("AppView checkers view: notifyObserverCheckers")
        self.observer.updateCheckers(stopFPSCheckers = self.getCORNERSCHECKERS, levelCheckers = self.levelCheckers.get(), cornersdataCheckers = self.allPointsCheckers, appName = self.appName, getCenterofFieldsCheckers = self.getCenterofFieldsCheckers, use_getCenterofFields = self.useButton_get_center.get())
    
    
    def continueGameCheckers(self):
        """
        continue a saved state of checkers game and their difficulty.
        the state of a checkers game is saved into the file "data/continue_save_state_Checkers.npy".
        this function checks if this file exists and load the saved information of index 0 (difficulty of the state)
        and set it into the level of checkers game.
        the function notify the controller to continue the State of game if the 
        file exists.


        :return: None 
        """
        
        logger.debug("AppView checkers view: continue Game checkers")
        self.playAudio(BEEPFILE)

        if os.path.isfile(SAVE_STATE_CHECKERS_GAME):
            arr = np.load(SAVE_STATE_CHECKERS_GAME, allow_pickle= True)

            if len(arr) != 0:
                self.levelCheckers.set(arr[0]) 
                self.notifyObserverCheckers()
                self.observer.continueGameCheckers()
            else:
                self.updateCheckersView(message = "Please delete manually the file `continue_pause.npy` in Folder `data`")
        

    
    def saveStateGameCheckers(self):
        """
        notify the controller to save the current state of chechers game and the difficulty of this state

        :return: None 
        """
        
        logger.debug("AppView checkers view: save current state of Game checkers")
        self.playAudio(BEEPFILE)
        self.observer.saveStateGameCheckers()


    def newGameCheckers(self):
        """
        notify the observer appController to start a new game and set the text of start button to restart

        :return: None
        """
        logger.debug("AppView checkers view: Start new Game checkers")
        self.playAudio(BEEPFILE)

        if self.useButton_get_center.get() == 1:
            self.updateCheckersView(message=None)
            self.observer.startGameCheckers()
            self.btnStartCheckers.config(text= "Restart")

        else:
            if os.path.isfile(CENTERSCHECKERSFIELDS):
                self.updateCheckersView(message=None)
                self.observer.startGameCheckers()
                self.btnStartCheckers.config(text= "Restart")
            else:
                self.playAudio(BEEPFILE_ERROR)
                self.updateCheckersView(message="Error ! Cannot find the data {}. Please use the button `Calibrate Checkers Gameboard to get the center of fields`".format(CENTERSCHECKERSFIELDS))
        


    def findConersCheckers(self):
        """
        starts new Calibration and ask user for 4 corner points

        :return: None
        """
        logger.debug("AppView: calibrate checkers view")
        if not self.getCORNERSCHECKERS:       
            self.playAudio(BEEPFILE)
            self.getCORNERSCHECKERS= True
            self.allPointsCheckers_new = self.allPointsCheckers
            self.allPointsCheckers =  None
            self.notifyObserverCheckers()
        
        self.btnCalibrateCheckers.config(font= ('verdana', 12, 'bold'), fg='red',
                                text= "Click on 4 Corners of Checkers Gameboard: <NW>, NE, SW, SE, or 'd' to delete last Corner or 'd' to stop the calibration")
        self.canvasCheckers.bind("<Button 1>",self.onMouseClickCheckers)
        return


    def findCenterFieldsCheckers(self):
        """
        start the process to get the centers of the 64 fields of checkers board.
        if the user use this button to get the center of fields a notification will been send to observer to start or stop 
        the process.

        :return: None
        """
        logger.debug("AppView: get center of fields of checkers gemaboard")
        # start the option to get the centers of fields  
        if self.getcalibrateCentersFieldsCheckers == False:
            self.notificationLabelCheckers.config(text= "When you don't see the centers of the fields, you can move the gameboard to a different position. Click on 'Get Centers now' when you see the centers of the 64 fields", background='red')
            self.btnCalibrateCheckers2.config(font= ('verdana', 12, 'bold'), fg='red', text="Get Centers now")
            self.getCenterofFieldsCheckers = False 
            self.notifyObserverCheckers()
            self.getCenterofFieldsCheckers = True
            self.getcalibrateCentersFieldsCheckers = True
            


        # when  the use click of "Get Centers now" the view notify the controller to save the centers of fields of gameboard.
        elif self.getcalibrateCentersFieldsCheckers == True:
            self.notificationLabelCheckers.config(background="white", text="")
            self.btnCalibrateCheckers2.config(font= ('verdana', 12, 'normal'), fg='black',
                                text= "Calibrate Checkers Gameboard to get the center of fields")
            self.getCenterofFieldsCheckers = True
            self.notifyObserverCheckers()
            time.sleep(0.1)
            self.getCenterofFieldsCheckers = None
            not self.notifyObserverCheckers()
            self.getcalibrateCentersFieldsCheckers = False

    
    def drawCornersAndGridCheckers(self):
        """
        draws grid to help the user to draw points for a new transformation matrix (calibration). 

        :return: None
        """
        #logger.debug("AppView: drawCornersAndGrid for Checkers View")
        if (self.getCORNERSCHECKERS):         
            w = WIDTH
            h = HEIGHT
            cv2.line(self.frameCheckers, (0,0), (w,h), (0,0,0), 1)
            cv2.line(self.frameCheckers, (0,h), (w,0), (0,0,0), 1)
            steps = 10
            deltaX = w // (steps * 2)
            deltaY = h // (steps * 2)
            xmin = 0
            ymin = 0
            xmax = w
            ymax = h
            for i in range (1, steps) :
                xmin+= deltaX
                ymin+= deltaY
                xmax-= deltaX
                ymax-= deltaY
                cv2.rectangle( self.frameCheckers, (xmin, ymin), (xmax, ymax), (0,0,0), 1)
        for (x, y) in self.cornersCheckers:
            cv2.circle(self.frameCheckers, (x, y), 10, (0, 255, 255), -1)

    

    def onMouseClickCheckers(self, mouseClick):
        """
        save the points during the calibration in the array self.cornersCheckers
        :param: mouseClick: click event

        :return: None
        """
        logger.debug("AppView onMouseClickCheckers to get pixel coordinate")
        if (len(self.cornersCheckers) < 4):
            self.playAudio(BEEPFILE)
            xCoord = mouseClick.x
            yCoord = mouseClick.y
            self.cornersCheckers.append([xCoord, yCoord])


    
    def updateTKCheckers(self):
        """
        update function for checkers View

        :return: None
        """
        if self.event.is_set():
            logger.debug("appView: Checkers thread stopped, exit ...")
            self.exit()

        if (self.getCORNERSCHECKERS and len(self.cornersCheckers)== 0 ):# to start new calibration
            self.findConersCheckers()
        if not self.resultFrameConsumer_Game.empty():
            self.frameCheckers = self.resultFrameConsumer_Game.get()
            if (not self.frameCheckers.size == 0):
                #logger.debug("AppView: camera frame available for Canvas in checkers View")
                self.drawCornersAndGridCheckers()  # indicate (x,y)-Coords for Calibration
                self.frameCheckers = cv2.cvtColor(self.frameCheckers, cv2.COLOR_BGR2RGB)
                self.photoCheckers = PIL.ImageTk.PhotoImage(master= self.canvasCheckers, image=PIL.Image.fromarray(self.frameCheckers))
                self.canvasCheckers.create_image(0, 0, image=self.photoCheckers, anchor=tkinter.NW)# draw camera frame on canvas
        
        if (len(self.cornersCheckers) == 1):
            self.btnCalibrateCheckers.config(text="Click on 4 Corners of Checkers Gameboard: NW, <NE>, SW, SE or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersCheckers) == 2):
            self.btnCalibrateCheckers.config(text="Click on 4 Corners of Checkers Gameboard: NW, NE, <SW>, SE or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersCheckers) == 3):
            self.btnCalibrateCheckers.config(text="Click on 4 Corners of Checkers Gameboard: NW, NE, SW, <SE> or 'd' to delete last Corner or 'd' to stop the calibration")
        elif (len(self.cornersCheckers) == 4):
            # if the 4 points has been defined, then start the perspective transform of opencv 
            self.canvasCheckers.unbind("<Button 1>")        # unregister Click-Handler
            self.btnCalibrateCheckers.config(font= ('verdana', 12, 'normal'), fg='black', text="Calibrate Checkers Gameboard for Zoom")
            self.getCORNERSCHECKERS =  False
            pts1 = np.float32(self.cornersCheckers)
            pts2 = np.float32([[0, 0], [WIDTH, 0],
                               [0, HEIGHT], [WIDTH, HEIGHT]])
        
            self.allPointsCheckers = cv2.getPerspectiveTransform(pts1, pts2)
            np.savetxt(CORNERSCHECKERS, self.allPointsCheckers, fmt='%f')# save the current matrix after the opencv transformation
            
            not self.notifyObserverCheckers()
            self.cornersCheckers=[]# empty the cornersTable to reuse it for a new calibration
            logger.debug("AppView: calibration in checkers View is finish")
        self.windowCheckers.after(self.delay_games_windows, self.updateTKCheckers)# update the Tkinter GUI after 100 milliseconds
    ############################################ checkers game end ############################################
        

    ############################################ Tower of Hanoi begin ############################################
    def towerofHanoi(self):
        """
        initialize view of tower of Hanoi Game

        :return: create the tower of hanoi View Component with a TKinter GUI from Home View
        """
        logger.debug("AppView: tower of hanoi View init...")
        self.playAudio(BEEPFILE)# play beep file by click
        self.window.withdraw()# hide Home View 
        self.appName = "menu_or_toh"# initialize self.appName to notify the appModel, to send the camera frame only to Queue for tower of hanoi or home View
        self.windowTOH = Toplevel(self.window)# initialize tower of hanoi View from Home View
        self.windowTOH.title('Tower of Hanoi Game')# set title of view 
        self.windowTOH.bind("<KeyPress>", self.onKeyPressTOH)# bind tower of hanoi view with keypress event (:q to exit the view, :d to delete points during the calibration)
        self.windowTOH.bind("<Escape>", self.onEscape)# bind tower of hanoi view with keypress event escape to exit the view
        
        # construct a frame to content the title of the Game
        tFrameTitle = Frame(self.windowTOH, relief=RIDGE, borderwidth=1)
        tFrameTitle.pack(fill=BOTH)

        headTOH = Label(tFrameTitle, anchor=CENTER, text='Welcome to Tower of Hanoi Game', font=('verdana', 20, 'bold'))
        headTOH.pack(fill='both', side='top', ipadx=20, ipady=20)

        # Canvas to contain a video 
        tkVideoFrameTOH = Frame(self.windowTOH, relief=RIDGE, borderwidth=10)
        tkVideoFrameTOH.pack(fill=BOTH,  expand=True)
        self.canvasTOH = tkinter.Canvas(tkVideoFrameTOH, width=VIEWWIDTH,height=VIEWHEIGHT)
        self.canvasTOH.pack()

        # construct a frame to content a empty place to show the notification of game, if available
        tFrame0 = Frame(self.windowTOH,  relief=RIDGE, borderwidth=1)
        tFrame0.pack(fill=BOTH, expand=True)

        self.notificationLabelTOH = Label(tFrame0, font=('verdana', 14, 'bold'))
        self.notificationLabelTOH.pack(ipadx=10, ipady=10, expand=True, fill='both', side='top')

        # construct a frame to hold the disc number
        tFrame1 = Frame(self.windowTOH,  relief=RIDGE, borderwidth=1)
        tFrame1.pack(fill=BOTH)
        
        textfield1 = Label(tFrame1, text="Please enter the number of disc: ", font=('verdana', 16))
        self.textinput1 = Entry (tFrame1)
        textfield1.pack(padx=10, pady=10, side='left')
        self.textinput1.pack(pady=10, side='left')

        # construct a frame to hold user information for from pegs
        tFrame12 = Frame(self.windowTOH,  relief=RIDGE, borderwidth=1)
        tFrame12.pack(fill=BOTH)
        textfield12 = Label(tFrame12, text="From pegs (A or B or C):", font=('verdana', 16))
        self.textinput12 = Entry (tFrame12)
        textfield12.pack(padx=10, pady=10, side='left')
        self.textinput12.pack(pady=10, side='left')

        # construct a frame to hold user information for to pegs
        tFrame121 = Frame(self.windowTOH,  relief=RIDGE, borderwidth=1)
        tFrame121.pack(fill=BOTH)
        textfield121 = Label(tFrame121, text="To Pegs (A or B or C):", font=('verdana', 16))
        self.textinput121 = Entry (tFrame121)
        textfield121.pack(padx=10, pady=10, side='left')
        self.textinput121.pack(pady=10, side='left')


        # construct a frame to get the pixel information to help the robot to find the pegs
        tFrame2 = Frame(self.windowTOH,  relief=RIDGE, borderwidth=1)
        tFrame2.pack(fill=BOTH)

        textfield2 = Label(tFrame2, text="Please use the Button 'Select Tower' and select the top of Tower", font=('verdana', 16))
        textfield2.pack(padx=10, pady=10, side='left')

        button2 = Button(tFrame2, text="Select Tower", font=('verdana', 18), width=20, borderwidth=3, command=self.selectTopTower)
        button2.pack(pady=10, side='left')

        # construct a frame to start the game tower of hanoi
        tFrameConfirm = Frame(self.windowTOH,  relief=RIDGE, borderwidth=1)
        tFrameConfirm.pack(fill=BOTH)
        btnConfirmTOH = Button(tFrameConfirm, text="Start Game", activebackground = "green", font=('verdana', 18, 'bold'), width=50, borderwidth=3, command=self.verifyInput_and_start_TOH)
        btnConfirmTOH.pack(ipadx=10, ipady=10, fill='both', side='bottom',expand=True)

        # construct a frame for exit Button
        tFrameExit = Frame(self.windowTOH,  relief=RIDGE, borderwidth=1)
        tFrameExit.pack(fill=BOTH)
        btnQuitTOH = Button(tFrameExit, text="Exit", activebackground = "red", font=('verdana', 18, 'bold'), width=50, borderwidth=3, command=self.exitTOH)
        btnQuitTOH.pack(ipadx=10, ipady=10, fill='both', side='bottom',expand=True)
        
        # notify observer
        self.notifyObserverTOH()

        # update function of tower of hanoi
        self.updateTKTOH()


    
    def exitTOH(self):
        """
        exit from chetower of hanoi View and restore (show) the Home view (root view), destroy tic tac toe view

        :return: None
        """
        logger.debug("AppView: Tower of Hanoi View exit ...")
        self.playAudio(BEEPFILE)
        time.sleep(0.2)
        self.windowTOH.destroy()
        self.window.deiconify()
        self.appName = "menu_or_toh"
        self.notifyObserverTOH()



    def onMouseClickselectTower(self, mouseClick):
        """
        help the user to find the top of pegs. the user select the top of tower and get the pixel 
        coordinate. this information help the robot to find the position of pegs
        :param: mouseClick: click event

        :return: None
        """
        logger.debug("AppView onMouseClickselectTower to get pixel coordinate")
        self.playAudio(BEEPFILE)
        xCoord = mouseClick.x
        yCoord = mouseClick.y
        self.counttower.append([xCoord, yCoord])

    

    def onKeyPressTOH(self, key):
        """
         Called when a key is pressed in the Tower of Hanoi View windows
         :param: key: key-event

         :return: None
        """
        logger.debug("AppView Tower of Hanoi view: keyPressed %s", key.char)
        if ( key.char == 'q') :
            self.onEscape(key)
        elif (key.char == 'd' and len (self.counttower)> 0) :
            self.counttower.pop()
        
        elif (key.char == 'd' and len (self.counttower) == 0) :
            self.canvasTOH.unbind("<Button 1>")        
            self.notificationLabelTOH.config(background="white", text="")
            self.stopselectTower = True

    def notifyObserverTOH(self):
        """
        to notify the observer (appController) with values:
        - dataTOH: content the enter information (from Pegs, to Pegs, temporyPegs) of the user, the Pixel coordinate of the 3 towers and the disc number
        - appName: to notify that Tower of hanoi view is launch. The Goal is to notify the appModel for it to send the camera frame to the currrent view running

        :return: None 
        """
        logger.debug("AppView Tower of Hanoi view: notifyObserverTOH")
        self.observer.updateTOH(dataTOH = self.dataTOH, appName = self.appName)

    
    def selectTopTower(self):
        """
        starts the process to get the 3 pixels coordinate of top of pegs

        :return: None
        """
        logger.debug("AppView: select top of pegs tower of hanoi")
        if self.stopselectTower:
            self.playAudio(BEEPFILE)
            self.stopselectTower = False
        
        self.notificationLabelTOH.config(background='orange',
                                text= "Click on top of Peg (A: left peg, B: middle peg, C: right peg): <A>, B, C or 'd' to delete last point or 'd' to stop")
        self.canvasTOH.bind("<Button 1>",self.onMouseClickselectTower)
        return


    def verifyInput_and_start_TOH(self):
        """
        get the enter values of user, get the pixels coordinates of pegs, verify the entry, notify the observer with this values and start the app tower of hanoi

        :return: None
        """
        self.playAudio(BEEPFILE)
        # get values (frompegs, topegs and disc number)
        discnumber = self.textinput1.get()
        fromPegs = self.textinput12.get()
        toPegs = self.textinput121.get()
        
        # transform lowercase letter in upper 
        fromPegs = fromPegs.upper()
        toPegs = toPegs.upper()

        # verify entry of user and pixel coordinate
        if (discnumber.isdigit() == True and self.storageTOH is not None and fromPegs in ('A','B','C') and toPegs in ('A','B','C')):
            if (fromPegs == toPegs):
                logger.error("AppView: error. the entry the values for tower of hanoi game is incorrect")
                self.playAudio(BEEPFILE_ERROR)
                self.notificationLabelTOH.config(background='red',
                                text= "Input Error: Number of disc or selection of pegs not correct. please Try again !")
            
            else:
                self.notificationLabelTOH.config(background="white", text="")
                discnumber = int (discnumber)
                ABC = ('A','B','C')
                setPegs =(fromPegs, toPegs)
                temporaryPegs = set(ABC).difference(set(setPegs)) # get temporary pegs from the entry (from and to pegs)
                temporaryPegs = next(iter(temporaryPegs))
                
                # convert the entry in number for the game engine
                if  fromPegs == "A":
                    fromPegs = 0
                elif fromPegs ==  "B":
                    fromPegs = 1
                elif fromPegs == "C":
                    fromPegs = 2

                if toPegs ==  "A":
                    toPegs = 0
                elif toPegs == "B":
                    toPegs = 1
                elif toPegs == "C":
                    toPegs = 2


                if  temporaryPegs == "A":
                    temporaryPegs = 0
                elif temporaryPegs == "B":
                    temporaryPegs = 1
                elif temporaryPegs == "C":
                    temporaryPegs = 2

                self.dataTOH = [discnumber, fromPegs, toPegs, temporaryPegs, self.storageTOH[0], self.storageTOH[1], self.storageTOH[2]]
                self.notifyObserverTOH()
                self.observer.startGameTOH()
                logger.debug("AppView: entry values is correct. Tower of Hanoi game will starting ...")
        else:
            logger.error("AppView: error. the entry the values for tower of hanoi game is incorrect")
            self.playAudio(BEEPFILE_ERROR)
            self.notificationLabelTOH.config(background='red',
                                text= "Input Error: Number of disc or selection of pegs not correct. please Try again !")


    

    def updateTKTOH(self):
        """
        update function for Tower of hanoi View

        :return: None
        """
        if self.event.is_set():
            logger.debug("appView: Tower of Hanoi thread stopped, exit ...")
            self.exit()
        if (not self.stopselectTower and len(self.counttower) == 0):# to start the functionality to get the pixel coordinates of tower
            self.selectTopTower()
        if (not self.frame.size == 0): # the same frame with Home view will been used
            #logger.debug("AppView: camera frame available for Canvas in Tower of Hanoi view")
            for (x, y) in self.counttower:
                # draw point with letter and color to help the user
                if len(self.counttower) == 1:
                    cv2.circle(self.frame, self.counttower[0], 10, (255, 120, 0), -1)
                    cv2.putText(self.frame, "A", (self.counttower[0][0]+20, self.counttower[0][1]+10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 120, 0), 3)
                elif len(self.counttower) == 2:
                    cv2.circle(self.frame, self.counttower[0], 10, (255, 120, 0), -1)
                    cv2.putText(self.frame, "A", (self.counttower[0][0]+20, self.counttower[0][1]+10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 120, 0), 3)
                    cv2.circle(self.frame, self.counttower[1], 10, (0, 255, 0), -1)
                    cv2.putText(self.frame, "B", (self.counttower[1][0]+20, self.counttower[1][1]+10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                elif len(self.counttower) == 3:
                    cv2.circle(self.frame, self.counttower[0], 10, (255, 120, 0), -1)
                    cv2.putText(self.frame, "A", (self.counttower[0][0]+20, self.counttower[0][1]+10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 120, 0), 3)
                    cv2.circle(self.frame, self.counttower[1], 10, (0, 255, 0), -1)
                    cv2.putText(self.frame, "B", (self.counttower[1][0]+20, self.counttower[1][1]+10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                    cv2.circle(self.frame, self.counttower[2], 10, (255, 110, 140), -1)
                    cv2.putText(self.frame, "C", (self.counttower[2][0]+20, self.counttower[2][1]+10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 110, 140), 3)
            self.photoTOH = PIL.ImageTk.PhotoImage(master= self.canvasTOH, image=PIL.Image.fromarray(self.frame))
            self.canvasTOH.create_image(0, 0, image=self.photoTOH, anchor=tkinter.NW)

        if (len(self.counttower) == 1):
            self.notificationLabelTOH.config(text="Click on top of Peg (A: left peg, B: middle peg, C: right peg): A, <B>, C or 'd' to delete last point or 'd' to stop")
        elif (len(self.counttower) == 2):
            self.notificationLabelTOH.config(text="Click on top of Peg (A: left peg, B: middle peg, C: right peg): A, B, <C> or 'd' to delete last point or 'd' to stop")
        elif (len(self.counttower) == 3):
            # if the 3 points has been defined, then save this in self.storageTOH, to send this to observer
            self.canvasTOH.unbind("<Button 1>")        
            self.notificationLabelTOH.config(background="white", text="")
            self.stopselectTower = True
            self.storageTOH = self.counttower
            self.counttower=[] 
            logger.debug("AppView: all pixel coordinates of pegs has been saved for tower of hanoi")
        self.windowTOH.after(self.delay_games_windows, self.updateTKTOH)  # update the Tkinter GUI after 100 milliseconds   
    ############################################ Tower of Hanoi end ############################################


    ############################################ AppView observer of AppController to get score of Tic Tac Toe and Checkers (begin) #######################################################

    def updateTicTTView(self, newScoreTicTT = None, message = None):
        """
        get Score and notification of Tic Tac Toe from Controller and draw this in view

        :return: None
        """
        if not message is None:
            try:
                self.notificationLabelTicTT.config(background='orange',
                                    text= message)
            except:
                logger.debug("AppView: Closed Tic Tac Toe Game ...")
        if message is None:
            try:
                self.notificationLabelTicTT.config(background='white', text="")
            except:
                logger.debug("AppView: Closed Tic Tac Toe Game ...")


        if (not newScoreTicTT is None):
            self.scoreTicTT= newScoreTicTT
            self.labelPlayerScoreTicTT.config(text= self.scoreTicTT[0])
            self.labelRobotScoreTicTT.config(text=self.scoreTicTT[1])
    
    def updateCheckersView(self, newScoreCheckers = None, message = None):
        """
        get Score and notification of Checkers from Controller and draw this in view

        :return: None
        """
        if not message is None:##############################
            try:
                self.notificationLabelCheckers.config(background='orange',
                                    text= message)
            except:
                logger.debug("AppView: Closed Checkers Game ...")

        if message is None:
            try:
                self.notificationLabelCheckers.config(background='white', text="")
            except:
                logger.debug("AppView: Closed Checkers Game ...")

        if (not newScoreCheckers is None):
            self.scoreCheckers= newScoreCheckers
            self.labelPlayerScoreCheckers.config(text= self.scoreCheckers[0])
            self.labelRobotScoreCheckers.config(text=self.scoreCheckers[1])

    ############################################ AppView observer of AppController to get score of Tic Tac Toe and Checkers (end) #######################################################

 
    ############################################ start mainLoop Tkinter (begin)#################################################### 
    
    def startMainloop(self) :
        # TKinter GUI-Mainloop
        self.window.mainloop()

    ############################################ start mainLoop Tkinter (end)###################################################### 