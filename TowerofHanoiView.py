from time import sleep
from tkinter import *
from tkinter import messagebox
from pygame import mixer
from config import *
import logging

# create logger
logger = logging.getLogger('towerOfHanoiView.py') 
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create log file
ch = logging.FileHandler('logs/towerOfHanoiView.log', mode='w')

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# Towers-of-Hanoi algorithm: move n pieces from a to b, using c
# as temporary.  For each move, call report()
def hanoi(n, a, b, c, report):
    if n <= 0:
        return
    hanoi(n-1, a, c, b, report)
    report(n, a, b)
    hanoi(n-1, c, b, a, report)


# The graphical interface with tkinter for Tower of Hanoi
class Tkhanoi():
    # Create our TK-objects        
    def __init__(self, disknumber, fromPegs, toPegs, temporaryPegs):
        logger.debug("towerOfHanoiView: towerOfHanoiView init...")
        self.var = False
        self.root = Tk() 
        self.root.bind("<Escape>", self.onEscape)
        self.root.geometry("800x250") 
        self.root.title('Tower of Hnaoi')

        self.fromPegs = fromPegs
        self.toPegs = toPegs
        self.temporaryPegs = temporaryPegs
        self.n = disknumber
        self.tk = tk = self.root
        self.canvas = c = Canvas(tk)
        c.pack()
        width, height = tk.getint(c['width']), tk.getint(c['height'])
        mixer.init()


        # Generate pegs
        pegwidth = 10
        pegheight = height/2
        pegdist = width/3
        x1, y1 = (pegdist-pegwidth)/2, height*1/3
        x2, y2 = x1+pegwidth, y1+pegheight
        self.pegs = []
        p = c.create_rectangle(x1, y1, x2, y2, fill='white')
        self.pegs.append(p)
        x1, x2 = x1+pegdist, x2+pegdist
        p = c.create_rectangle(x1, y1, x2, y2, fill='white')
        self.pegs.append(p)
        x1, x2 = x1+pegdist, x2+pegdist
        p = c.create_rectangle(x1, y1, x2, y2, fill='white')
        self.pegs.append(p)

        c.create_text(63 ,65, text="A", font=("Helvetica", 20))
        c.create_text(189 ,65, text="B", font=("Helvetica", 20))
        c.create_text(315 ,65, text="C", font=("Helvetica", 20))
        self.tk.update()
    

        # Generate pieces
        pieceheight = pegheight/16
        maxpiecewidth = pegdist*2/3
        minpiecewidth = 2*pegwidth
        self.pegstate = [[], [], []]
        self.pieces = {}
        x1, y1 = (pegdist-maxpiecewidth)/2, y2-pieceheight-2
        x2, y2 = x1+maxpiecewidth, y1+pieceheight
        dx = (maxpiecewidth-minpiecewidth) / (2*max(1, disknumber-1))
        for i in range(disknumber, 0, -1):
            p = c.create_rectangle(x1, y1, x2, y2, fill='green')
            self.pieces[i] = p
            self.pegstate[0].append(i)
            x1, x2 = x1 + dx, x2-dx
            y1, y2 = y1 - pieceheight-2, y2-pieceheight-2
            self.tk.update()
            self.tk.after(25)

    def onEscape(self, event):      # catch ESC-key
        self.exit()

    def playAudio(self, audiofilename): # play audio
        alert = mixer.Sound(audiofilename)
        alert.play()

    def exit(self): # destroy root 
        self.playAudio(BEEPFILE)
        self.root.destroy()

    # Run-function
    def run(self):
        try:
            if (self.fromPegs==0):
                self.var = True
                hanoi(self.n, self.fromPegs, self.toPegs, self.temporaryPegs, self.report)
                self.var = False
                
            elif (self.fromPegs== 1):
                hanoi(self.n, 0, 1, 2, self.report)
                sleep(1)
                self.var = True
                hanoi(self.n, self.fromPegs, self.toPegs, self.temporaryPegs, self.report)
                self.var = False
                
            elif (self.fromPegs== 2):
                hanoi(self.n, 0, 1, 2, self.report)
                hanoi(self.n, 1, 2, 0, self.report)
                sleep(1)
                self.var = True
                hanoi(self.n, self.fromPegs, self.toPegs, self.temporaryPegs, self.report)
                self.var = False
                    
            # messagebox.showinfo("Information", "Game is over !")
            self.root.after(3000, self.root.destroy())
            # self.root.mainloop()
        except:
            logger.debug("towerOfHanoiView: thread stopped, exit ...")        

    # Reporting callback for the actual hanoi function
    def report(self, i, a, b):
        if self.pegstate[a][-1] != i: raise RuntimeError 
        del self.pegstate[a][-1]
        p = self.pieces[i]
        c = self.canvas

        # Lift the piece above peg a
        ax1, ay1, ax2, ay2 = c.bbox(self.pegs[a])
        while 1:
            x1, y1, x2, y2 = c.bbox(p)
            if y2 < ay1: break
            c.move(p, 0, -1)
            self.tk.update()

        # Move it towards peg b
        bx1, by1, bx2, by2 = c.bbox(self.pegs[b])
        newcenter = (bx1+bx2)/2
        while 1:
            x1, y1, x2, y2 = c.bbox(p)
            center = (x1+x2)/2
            if center == newcenter: break
            if center > newcenter: c.move(p, -1, 0)
            else: c.move(p, 1, 0)
            self.tk.update()

        # Move it down on top of the previous piece
        pieceheight = y2-y1
        newbottom = by2 - pieceheight*len(self.pegstate[b]) - 2
        while 1:
            x1, y1, x2, y2 = c.bbox(p)
            if y2 >= newbottom: break
            c.move(p, 0, 1)
            self.tk.update()

        # Update peg state
        self.pegstate[b].append(i)
        if (self.var == True):
            sleep(8)
