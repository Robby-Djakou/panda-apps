"""
the presented code comes from the github https://github.com/dimitrijekaranfilovic/checkers/blob/master/checkers.py 
and has been modified for the creation of our checkers application. 

This code contains the alpha beta pruning and minimax algorithms.
"""

from copy import deepcopy
import time
import math
import numpy as np
from config import *
import _thread # to create a new thread 
import logging

# create logger
logger = logging.getLogger('checkers.py') 
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create log file
ch = logging.FileHandler('logs/checkers.log', mode='w')

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

class Node:
    
    def __init__(self, board, move=None):
        """
        the Node class generate the possible availables move and jumps for the computer.
        These informations are important for the minimax and alpha beta prunning 
        :param: board: current array of checker gameboard
        :param: move: available computer moves

        :return: None
        """
        logger.debug("Node: Node init...")
        self.board = board 
        self.move = move 


    def get_children(self, maximizing_player, mandatory_jumping):
        """
        get the available moves or jumps of the maximizing_player (Computer with c or C) or minimizing_player (player with b or B)
        :param: maximizing_player: verify if the current player is minimizing player or  maximizing player
        :param: mandatory_jumping: option to use mandatory jump or not for both player 

        :return: children_states: array of current state of Node with the current gameboard after the possible moves and jumps or moves of computer or of the player for the minimax and alpha beta algorithm
        """
        current_state = deepcopy(self.board) # copy of array
        available_moves = [] # array to save available move of player or computer 
        children_states = [] # array to save the next status of Node class (children of current Node class) 
        big_letter = "" 
        queen_row = 0 
        if maximizing_player is True: # if maximizing player, then find availables moves or possibles jumps for the computer 
            available_moves = Checkers.find_available_moves(current_state, mandatory_jumping) # verify if mandatory jump is True, then get available jumps or moves
            big_letter = "C" # when the computer (c) become King (C)
            queen_row = 7 # first index of the two-dimensional array of current game board, if the computer come to this position, he become king
        else: # if minimizing player, then find availables moves or possibles jumps for the player 
            available_moves = Checkers.find_player_available_moves(current_state, mandatory_jumping) # verify if mandatory jump is True, then get available jumps or moves
            big_letter = "B" # when the player (b) become King (B)
            queen_row = 0 # first index of the two-dimensional array of current game board, if the computer come to this position, he become king
        
        """
        use availables moves or jumps and the result array of gameboard after the modification into the Node,
        save the result Nodes into array children_states as child of the current state of Node and return this array
        """
        for i in range(len(available_moves)): 
            old_i = available_moves[i][0]
            old_j = available_moves[i][1]
            new_i = available_moves[i][2]
            new_j = available_moves[i][3]
            state = deepcopy(current_state)
            Checkers.make_a_move(state, old_i, old_j, new_i, new_j, big_letter, queen_row)
            children_states.append(Node(state, [old_i, old_j, new_i, new_j]))
        return children_states

    def get_board(self):
        """
        get current array of checker gameboard
        :param: None

        :return: self.board: gameboard
        """
        return self.board


class Checkers:
    """
    class to implement the alpha-beta-pruning and the minimax algorithms.
    :param: observerController: Checkers acts as Observable, observer is appController
    :param: matrix: array for the current gameboard so that the minimax and alpha-beta-pruning algorithms can generate a move

    :return: moves of computers
    """
    def __init__(self, observerController, matrix):
        logger.debug("Checkers: Checkers init...")
        
        self.observerController = observerController
        self.matrix = matrix.tolist() # convert to numpy array to list array for the algorithm

        self.player_turn = True # Player plays first
        self.computer_pieces = 12 # number of computer pieces at the start of game
        self.player_pieces = 12 # number of player pieces at the start of game
        self.available_moves = [] # array to save the available moves
        self.mandatory_jumping = False # initialize the mandatoring jumpy to False for 2 players 

        self.message = None # initialize the message to notify the appController and the appController can send this to appView
        self.final_score = [0, 0] # initialize the score of the player and the score of computer


    def get_player_input(self, fromInd, toInd):
        """
        get Input of the player, verify the move of player and write this into the array gameboardy.
        :param: fromInd: tuples of the position of player piece, that has been taken
        :param: toInd: tuples of the new position of player piece

        :return: False: if the move is not valid
                 True: if the move is valid
        """
        available_moves = Checkers.find_player_available_moves(self.matrix, self.mandatory_jumping) # get the available moves or jumps from the current array gameboard of te player 
        if len(available_moves) == 0: # if the not available moves, then verify the number of pieces of both player
            if self.computer_pieces > self.player_pieces: # if the computer has more piece than the player, then the computer won the game
                self.message =   "You have no moves left, and you have fewer pieces than the computer. :( :( :( YOU LOSE! ): ): ):" 
                self.scoreRobot += 1 # increment the score of the computer
                self.observerController.notifyObserverViewCheckers(newScore=self.final_score, message = self.message) # notify the appController with the score informations of both players and the notification message 
                _thread.start_new_thread(self.observerController.playAudio, (GAMEOVER,)) # 
                _thread.start_new_thread(self.observerController.doAudio, (WIN_FRANKA,))

            else: # if the computer has few piece than the player, then the computer won the game
                self.message = "You have no available moves. --- GAME ENDED! ---"
                self.observerController.notifyObserverViewCheckers(message = self.message)
                _thread.start_new_thread(self.observerController.doAudio, (TIEGAME,))


        coord1 = fromInd 
        coord2 = toInd
        old = coord1.split(",") # get the x and y coordinates of the start position of the piece, that the player has moved
        new = coord2.split(",") # get the x and y coordinates of the cible position where the piece will be moved

        old_i = old[0] 
        old_j = old[1]
        new_i = new[0]
        new_j = new[1]

        move = [int(old_i), int(old_j), int(new_i), int(new_j)] # do a array to save the x,y start position of player piece and x,y cible position of this piece 
        
        # # find the player move in the available moves or available jumps
        if move not in available_moves: # if the player move is not in the available jumps or moves
            self.message = "Illegal user move! please try again !"
            self.observerController.notifyObserverViewCheckers(message = self.message)
            _thread.start_new_thread(self.observerController.doAudio, (self.message,))

            return False
        else: # if the player move is in the available jumps or moves
            #set the number of pieces of both player to 0
            self.player_pieces = 0 
            self.computer_pieces = 0

            # inform the appController about the player move
            self.message = "Player has moved black piece from ({},{}) to ({},{})".format(old[0], old[1], new[0], new[1])
            self.observerController.notifyObserverViewCheckers(message = self.message)
            _thread.start_new_thread(self.observerController.doAudio, (PlAYER_PLAY,))
   
            
            Checkers.make_a_move(self.matrix, int(old_i), int(old_j), int(new_i), int(new_j), "B", 0) # update the current gameboard after a jump or after a move of the player and verify if the player become king 
            for m in range(8):
                for n in range(8):
                    if self.matrix[m][n][0] == "c" or self.matrix[m][n][0] == "C": # write the position changes of the computer pieces into the array of gameboard
                        self.computer_pieces += 1 # count number of computer pieces 
                    elif self.matrix[m][n][0] == "b" or self.matrix[m][n][0] == "B": # write the position changes of the player pieces into the array of gameboard
                        self.player_pieces += 1 # count number of player pieces 
            return True 

    @staticmethod
    def find_available_moves(board, mandatory_jumping):
        """
        find available moves of the computer pieces or possible available moves 
        the computer's pieces are written in the form 'cxy'.
        :param: board: current array game board
        :param: mandatory_jumping:option to use mandatory jump or not for both player 

        :return: available_jumps: computer can do a jump or a move 
                 available_jumps: computer must do one of the available jump (mandatory)
                 available_moves: computer can do one of the available move
        """
        available_moves = []
        available_jumps = []
        for m in range(8):
            for n in range(8):
                if board[m][n][0] == "c": # verify if the value of the array beginnt with 'c' (computer)
                    if Checkers.check_moves(board, m, n, m + 1, n + 1): # verify if the current move is authorized (cible position is bottom right from current position)
                        available_moves.append([m, n, m + 1, n + 1]) # if the current move is authorized then save this move into the available moves
                    if Checkers.check_moves(board, m, n, m + 1, n - 1): # verify if the current move is authorized (cible position is bottom left from current position)
                        available_moves.append([m, n, m + 1, n - 1])
                    if Checkers.check_jumps(board, m, n, m + 1, n - 1, m + 2, n - 2): # jump the computer piece over the player piece (cible position is bottom left from current position)
                        available_jumps.append([m, n, m + 2, n - 2])
                    if Checkers.check_jumps(board, m, n, m + 1, n + 1, m + 2, n + 2): # jump the computer piece over the player piece (cible position is bottom right from current position)
                        available_jumps.append([m, n, m + 2, n + 2])
                elif board[m][n][0] == "C": # verify if the value of the array beginnt with 'C' (computer has becommed king)
                    if Checkers.check_moves(board, m, n, m + 1, n + 1):# verify if the current move is authorized (cible position is bottom right from current position)
                        available_moves.append([m, n, m + 1, n + 1]) # if the current move is authorized then save this move into the available moves
                    if Checkers.check_moves(board, m, n, m + 1, n - 1):# verify if the current move is authorized (cible position is bottom left from current position)
                        available_moves.append([m, n, m + 1, n - 1])
                    if Checkers.check_moves(board, m, n, m - 1, n - 1): # verify if the current move is authorized (cible position is top left from current position)
                        available_moves.append([m, n, m - 1, n - 1])
                    if Checkers.check_moves(board, m, n, m - 1, n + 1): # verify if the current move is authorized (cible position is top right from current position)
                        available_moves.append([m, n, m - 1, n + 1])
                    if Checkers.check_jumps(board, m, n, m + 1, n - 1, m + 2, n - 2): # jump the computer piece over the player piece (cible position is bottom left from current position)
                        available_jumps.append([m, n, m + 2, n - 2])
                    if Checkers.check_jumps(board, m, n, m - 1, n - 1, m - 2, n - 2): # jump the computer piece over the player piece (cible position is top left from current position)
                        available_jumps.append([m, n, m - 2, n - 2])
                    if Checkers.check_jumps(board, m, n, m - 1, n + 1, m - 2, n + 2): # jump the computer piece over the player piece (cible position is top right from current position)
                        available_jumps.append([m, n, m - 2, n + 2])
                    if Checkers.check_jumps(board, m, n, m + 1, n + 1, m + 2, n + 2): # jump the computer piece over the player piece (cible position is bottom right from current position)
                        available_jumps.append([m, n, m + 2, n + 2])
        if mandatory_jumping is False: # if mandatory jumping is not activated
            available_jumps.extend(available_moves) # add elements of  available_moves to available_jumps. the computer can do a jump or a move
            return available_jumps
        elif mandatory_jumping is True: # if mandatory jumping is activated
            if len(available_jumps) == 0: # if not jump over player available, then use the computer must play his move 
                return available_moves
            else: # if jump over player available, the player must jump over the player 
                return available_jumps

    @staticmethod
    def check_jumps(board, old_i, old_j, via_i, via_j, new_i, new_j):
        """
        verify if the jump of the computer is authorized
        :param: board: current array gameboard
        :param: old_i: first index of the array gameboard with 2 dimensions (x-coordinate of the start position of the player piece)
        :param: old_j: second index of the array gameboard with 2 dimensions (y-coordinate of the start position of the player piece)
        :param: via_i: x-coordinate of the position of the player piece, that has been jumped
        :param: via_j: y-coordinate of the position of the player piece, that has been jumped
        :param: new_i: first index of the array gameboard with 2 dimension (x-coordinate of the cible position of the player piece)
        :param: new_j: second index of the array gameboard with 2 dimension (y-coordinate of the cible position of the player piece)

        :return: False: not authorized
                 True: authorized 
        """
        
        if new_i > 7 or new_i < 0: # if x-coordinate of the cible position out of range
            return False
        if new_j > 7 or new_j < 0: # if y-coordinate of the cible position out of range
            return False
        if board[via_i][via_j] == "---": # if the position of the piece, that has been jumped is empty
            return False
        if board[via_i][via_j][0] == "C" or board[via_i][via_j][0] == "c": # if the piece, that has been jumped is for the computer
            return False
        if board[new_i][new_j] != "---": # if the cible position of the computer piece is not empty
            return False
        if board[old_i][old_j] == "---": # if the start position of the computer piece is empty
            return False
        if board[old_i][old_j][0] == "b" or board[old_i][old_j][0] == "B": # if the computer grab the player piece (b: player piece, B: player piece if he becomes king)
            return False
        return True

    @staticmethod
    def check_moves(board, old_i, old_j, new_i, new_j):
        """
        verify if the move of the computer is authorized
        :param: board: current array gameboard
        :param: old_i: first index of the array gameboard with 2 dimensions (x-coordinate of the start position of the player piece)
        :param: old_j: second index of the array gameboard with 2 dimensions (y-coordinate of the start position of the player piece)
        :param: new_i: first index of the array gameboard with 2 dimension (x-coordinate of the cible position of the player piece)
        :param: new_j: second index of the array gameboard with 2 dimension (y-coordinate of the cible position of the player piece)

        :return: False: not authorized
                 True: authorized 
        """

        if new_i > 7 or new_i < 0: # if x-coordinate of the cible position out of range
            return False
        if new_j > 7 or new_j < 0: # if y-coordinate of the cible position out of range
            return False
        if board[old_i][old_j] == "---": # if the start position of the computer piece is empty
            return False
        if board[new_i][new_j] != "---": # if the cible position of the computer piece is not empty
            return False
        if board[old_i][old_j][0] == "b" or board[old_i][old_j][0] == "B": # if the computer grab the player piece (b: player piece, B: player piece if he becomes king)
            return False
        if board[new_i][new_j] == "---": # if the cible position of the computer piece is  empty, the computer can do the move on this position
            return True

    @staticmethod
    def calculate_heuristics(board):
        """
        heuristics calculation of all the position inside the array of the current gameboard

        :param: board: current array gameboard

        :return: heuristics value 
        """
        result = 0
        mine = 0
        opp = 0
        for i in range(8):
            for j in range(8):
                if board[i][j][0] == "c" or board[i][j][0] == "C":
                    mine += 1

                    if board[i][j][0] == "c":
                        result += 5
                    if board[i][j][0] == "C":
                        result += 10
                    if i == 0 or j == 0 or i == 7 or j == 7:
                        result += 7
                    if i + 1 > 7 or j - 1 < 0 or i - 1 < 0 or j + 1 > 7:
                        continue
                    if (board[i + 1][j - 1][0] == "b" or board[i + 1][j - 1][0] == "B") and board[i - 1][
                        j + 1] == "---":
                        result -= 3
                    if (board[i + 1][j + 1][0] == "b" or board[i + 1][j + 1] == "B") and board[i - 1][j - 1] == "---":
                        result -= 3
                    if board[i - 1][j - 1][0] == "B" and board[i + 1][j + 1] == "---":
                        result -= 3

                    if board[i - 1][j + 1][0] == "B" and board[i + 1][j - 1] == "---":
                        result -= 3
                    if i + 2 > 7 or i - 2 < 0:
                        continue
                    if (board[i + 1][j - 1][0] == "B" or board[i + 1][j - 1][0] == "b") and board[i + 2][
                        j - 2] == "---":
                        result += 6
                    if i + 2 > 7 or j + 2 > 7:
                        continue
                    if (board[i + 1][j + 1][0] == "B" or board[i + 1][j + 1][0] == "b") and board[i + 2][
                        j + 2] == "---":
                        result += 6

                elif board[i][j][0] == "b" or board[i][j][0] == "B":
                    opp += 1

        return result + (mine - opp) * 1000

    @staticmethod
    def find_player_available_moves(board, mandatory_jumping):
        """
        find available moves of the player pieces or possible available moves 
        the player's pieces are written in the form 'bxy'.
        :param: board: current array game board
        :param: mandatory_jumping: option to use mandatory jump or not for both player 

        :return: available_jumps: player can do a jump or a move 
                 available_jumps: player must do one of the available jump (mandatory)
                 available_moves: player can do one of the available move
        """
        available_moves = []
        available_jumps = []
        for m in range(8):
            for n in range(8):
                if board[m][n][0] == "b": # verify if the value of the array beginnt with 'b' (player)
                    if Checkers.check_player_moves(board, m, n, m - 1, n - 1): # verify if the current move is authorized (cible position is Top left from current position)
                        available_moves.append([m, n, m - 1, n - 1]) # if the current move is authorized then save this move into the available moves
                    if Checkers.check_player_moves(board, m, n, m - 1, n + 1): # verify if the current move is authorized (cible position is Top right from current position)
                        available_moves.append([m, n, m - 1, n + 1])
                    if Checkers.check_player_jumps(board, m, n, m - 1, n - 1, m - 2, n - 2): # jump the player piece over the computer piece (cible position is Top left from current position)
                        available_jumps.append([m, n, m - 2, n - 2])
                    if Checkers.check_player_jumps(board, m, n, m - 1, n + 1, m - 2, n + 2):# jump the player piece over the computer piece (cible position is Top right from current position) 
                        available_jumps.append([m, n, m - 2, n + 2]) 
                elif board[m][n][0] == "B": # # verify if the value of the array beginnt with 'B' (player has becommed king)
                    if Checkers.check_player_moves(board, m, n, m - 1, n - 1): # verify if the current move is authorized (cible position is Top left from current position)
                        available_moves.append([m, n, m - 1, n - 1])  # if the current move is authorized then save this move into the available moves
                    if Checkers.check_player_moves(board, m, n, m - 1, n + 1): # verify if the current move is authorized (cible position is Top right from current position)
                        available_moves.append([m, n, m - 1, n + 1])
                    if Checkers.check_player_jumps(board, m, n, m - 1, n - 1, m - 2, n - 2): # jump the player piece over the computer piece (cible position is Top left from current position)
                        available_jumps.append([m, n, m - 2, n - 2])
                    if Checkers.check_player_jumps(board, m, n, m - 1, n + 1, m - 2, n + 2): # jump the player piece over the computer piece (cible position is Top right from current position)
                        available_jumps.append([m, n, m - 2, n + 2])
                    if Checkers.check_player_moves(board, m, n, m + 1, n - 1): # verify if the current move is authorized (cible position is bottom left from current position)
                        available_moves.append([m, n, m + 1, n - 1])
                    if Checkers.check_player_jumps(board, m, n, m + 1, n - 1, m + 2, n - 2): # jump the player piece over the computer piece (cible position is bottom left from current position)
                        available_jumps.append([m, n, m + 2, n - 2])
                    if Checkers.check_player_moves(board, m, n, m + 1, n + 1): # verify if the current move is authorized (cible position is bottom right from current position)
                        available_moves.append([m, n, m + 1, n + 1])
                    if Checkers.check_player_jumps(board, m, n, m + 1, n + 1, m + 2, n + 2): # jump the player piece over the computer piece (cible position is bottom right from current position)
                        available_jumps.append([m, n, m + 2, n + 2])
        if mandatory_jumping is False: # if mandatory jumping is not activated
            available_jumps.extend(available_moves) # add elements of  available_moves to available_jumps. the player can do a jump or a move
            return available_jumps 
        elif mandatory_jumping is True: # if mandatory jumping is activated
            if len(available_jumps) == 0: # if not jump over computer available, then use the player must play his move 
                return available_moves 
            else: # if jump over computer available, the player must jump over the computer 
                return available_jumps

    @staticmethod
    def check_player_moves(board, old_i, old_j, new_i, new_j):
        """
        verify if the move of the player is authorized
        :param: board: current array gameboard
        :param: old_i: first index of the array gameboard with 2 dimensions (x-coordinate of the start position of the player piece)
        :param: old_j: second index of the array gameboard with 2 dimensions (y-coordinate of the start position of the player piece)
        :param: new_i: first index of the array gameboard with 2 dimension (x-coordinate of the cible position of the player piece)
        :param: new_j: second index of the array gameboard with 2 dimension (y-coordinate of the cible position of the player piece)

        :return: False: not authorized
                 True: authorized 
        """
        if new_i > 7 or new_i < 0: # if x-coordinate of the cible position out of range
            return False
        if new_j > 7 or new_j < 0: # if y-coordinate of the cible position out of range
            return False
        if board[old_i][old_j] == "---": # if the start position of the player piece is empty
            return False
        if board[new_i][new_j] != "---": # if the cible position of the player piece is not empty
            return False
        if board[old_i][old_j][0] == "c" or board[old_i][old_j][0] == "C": # if the player grab the computer piece (c: computer piece, C: computer piece if he becomes king)
            return False
        if board[new_i][new_j] == "---": # if the cible position of the player piece is  empty, the player can do the move on this position
            return True

    @staticmethod
    def check_player_jumps(board, old_i, old_j, via_i, via_j, new_i, new_j):
        """
        verify if the jump of the player is authorized
        :param: board: current array gameboard
        :param: old_i: first index of the array gameboard with 2 dimensions (x-coordinate of the start position of the player piece)
        :param: old_j: second index of the array gameboard with 2 dimensions (y-coordinate of the start position of the player piece)
        :param: via_i: x-coordinate of the position of the player piece, that has been jumped
        :param: via_j: y-coordinate of the position of the player piece, that has been jumped
        :param: new_i: first index of the array gameboard with 2 dimension (x-coordinate of the cible position of the player piece)
        :param: new_j: second index of the array gameboard with 2 dimension (y-coordinate of the cible position of the player piece)

        :return: False: not authorized
                 True: authorized 
        """
        if new_i > 7 or new_i < 0: # if x-coordinate of the cible position out of range
            return False
        if new_j > 7 or new_j < 0: # if y-coordinate of the cible position out of range
            return False
        if board[via_i][via_j] == "---": # if the position of the piece, that has been jumped is empty
            return False
        if board[via_i][via_j][0] == "B" or board[via_i][via_j][0] == "b": # if the piece, that has been jumped is for the player
            return False
        if board[new_i][new_j] != "---": # if the cible position of the player piece is not empty
            return False
        if board[old_i][old_j] == "---": # if the start position of the player piece is empty
            return False
        if board[old_i][old_j][0] == "c" or board[old_i][old_j][0] == "C": # if the player grab the computer piece (c: computer piece, C: computer piece if he becomes king)
            return False
        return True

    def evaluate_states(self):
        """
        minimax and alpha beta pruning algorithm to generate the move or jump of computer with the current array gameboard
        :param: None

        :return: str(move[0]), str(move[1]), str(move[2]), str(move[3]): x(move[0]),y(move[1])- start position of the computer move 
                                                                       : x(move[2]),y(move[3])- cible position of the computer move 
        """
        t1 = time.time() # get the current time to calculate the time reaction of algorithm
        current_state = Node(deepcopy(self.matrix)) # copy the current gameboard and use Node to get the availables moves and jumps of the computer in the current gameboard 

        first_computer_moves = current_state.get_children(True, self.mandatory_jumping) # # get Node instance of the current availables moves or jumps of maximizing player
        if len(first_computer_moves) == 0: # if not availables moves or jumps of maximizing player, then count the game pieces of both player
            if self.player_pieces > self.computer_pieces: # if the player has more piece than the computer, then the player won the game
                self.message = "Computer has no available moves left, and you have more pieces left. :) :) :) YOU WIN! (: (: (:"
                self.final_score[0] += 1 
                self.observerController.notifyObserverViewCheckers(newScore=self.final_score, message = self.message)
                _thread.start_new_thread(self.observerController.playAudio, (GAMEWIN,))
                _thread.start_new_thread(self.observerController.doAudio, (WIN_PLAYER,))

            else:
                self.message = "Computer has no available moves left. --- GAME ENDED! ---"
                self.observerController.notifyObserverViewCheckers(message = self.message)
                _thread.start_new_thread(self.observerController.doAudio, (TIEGAME,))
        else: # if availables moves or jumps of maximizing player
            dict = {}
            for i in range(len(first_computer_moves)):
                child = first_computer_moves[i] # get child of Node class with availables jumps or moves
                value = Checkers.minimax(child.get_board(), 4, -math.inf, math.inf, False, self.mandatory_jumping) # use alpha beta pruning algorithm and minimax with all array gameboard of the Node kind instance with a depth of 4 through these array gameboards
                dict[value] = child 
            if len(dict.keys()) == 0: # not moves or jumps availables
                self.message = "Computer has cornered itself. :) :) :) YOU WIN! (: (: (:"
                self.final_score[0] += 1
                self.observerController.notifyObserverViewCheckers(newScore=self.final_score, message = self.message)
                _thread.start_new_thread(self.observerController.playAudio, (GAMEWIN,))
                _thread.start_new_thread(self.observerController.doAudio, (WIN_PLAYER,))
            
            else:
                new_board = dict[max(dict)].get_board()
                move = dict[max(dict)].move # get the best move from the dictionary
                self.matrix = new_board # update the current array gameboard with the new computer move
                t2 = time.time()
                diff = t2 - t1
                self.message = "Computer has moved (" + str(move[0]) + "," + str(move[1]) + ") to (" + str(move[2]) + "," + str(
                    move[3]) + ")." + " It took him " + str(round(diff, 5)) + " seconds."
                _thread.start_new_thread(self.observerController.doAudio, (FRANKA_PLAY,))
                self.observerController.notifyObserverViewCheckers(message = self.message)
                return str(move[0]), str(move[1]), str(move[2]), str(move[3])

    @staticmethod
    def minimax(board, depth, alpha, beta, maximizing_player, mandatory_jumping):
        """
        alpha beta pruning algorith for checker game to get the maximum evaluation of computer (best move for computer) and the minimum evaluation of player
        :param: board: current array of checker gameboard
        :param: depth: depth of tree (number of time that the recursive function between maximizer and minimizer player must be run or the reverse)
        :param: alpha: The best choice we have found so far at any point along the path of Maximizer. The initial value of alpha is -∞
        :param: beta:  The best choice we have found so far at any point along the path of Minimizer. The initial value of beta is +∞.
        :param: maximizing_player: set True for maximizing Player or False for minimizing Player
        :param: mandatory_jumping: option to use mandatory jump or not for both player 

        :return: max_eval: maximum evaluation  for computer (maximizing Player)
                 min_eval: minimum evaluation  for player (minimizing Player)
        """
        if depth == 0: # if depth is null, then get the evaluation value of end of node of tree 
            return Checkers.calculate_heuristics(board) # heuristic evaluation of all the position in the checker gameboard
        current_state = Node(deepcopy(board)) 

        """
            The maximum player determines the possible moves 
            and jumps of the child nodes from the gameboard 
            array generated by the child nodes and passes the 
            node instance containing all this information to 
            the minimum player. The minimum player does the 
            same and determines the possible moves and jumps 
            from the child nodes generated by the maximum player
            and passes the node instance containing all this 
            information to the maximum player. All this will 
            be done in a loop, until the deph value is 0. Each 
            time the maximum player passes to the minimum or vice 
            versa, the depth is reduced by 1. Once the depth is equal 
            to 0, the heuristic calculation of the end nodes will be determined. 
            From the heuristic result, the maximum (if it is the maximum player) 
            or minimum (if it is the minimum player) value will be determined between 
            the evaluation of the end node and -infinity (computer) or +infinity (player). 
            The resulting value of the maximum or minimum calculation will be assigned 
            to +infinity or -infinity and the new data will be compared in turn with the top nodes 
            of the tree depending on whether it is the maximum or the minimum until the 
            top of the tree is reached, i.e. the Maximum player (computer). If during 
            the calculation of the maximum or minimum evaluations alpha is greater than 
            or equal to beta then there will be a pruning.  
        """
        if maximizing_player is True: # maximizer player 
            max_eval = -math.inf
            for child in current_state.get_children(True, mandatory_jumping):
                ev = Checkers.minimax(child.get_board(), depth - 1, alpha, beta, False, mandatory_jumping)
                max_eval = max(max_eval, ev)
                alpha = max(alpha, ev) 
                if beta <= alpha: # pruning
                    break
            return max_eval # maximum evaluation  for computer (maximizing Player)
        else: # minimizing player  
            min_eval = math.inf
            for child in current_state.get_children(False, mandatory_jumping):
                ev = Checkers.minimax(child.get_board(), depth - 1, alpha, beta, True, mandatory_jumping)
                min_eval = min(min_eval, ev)
                beta = min(beta, ev) 
                if beta <= alpha: # pruning
                    break
            return min_eval # minimum evaluation  for player (minimizing Player)

    @staticmethod
    def make_a_move(board, old_i, old_j, new_i, new_j, big_letter, queen_row):
        """
        when the player does  a jump over a computer piece or the computer 
        do a jump over a player piece, this piece must be removed and remplace
        with empty place.
        :param: board: current array gameboard
        :param: old_i: first index of the array gameboard with 2 dimensions (x-coordinate of the start position of the player piece)
        :param: old_j: second index of the array gameboard with 2 dimensions (y-coordinate of the start position of the player piece)
        :param: new_i: first index of the array gameboard with 2 dimension (x-coordinate of the cible position of the player piece)
        :param: new_j: second index of the array gameboard with 2 dimension (y-coordinate of the cible position of the player piece)
        :param: big_letter: king Letter of Player (B) or king letter of computer (C)
        :param: queen_row: King index in array gameboard, if the player or the computer come to these indexs, then they become king (index 0 for player or index 7 for computer)
        
        :return: None
        """
        letter = board[old_i][old_j][0] # get the current letter (b for player, B for king player, c for computer or C for king computer)
        i_difference = old_i - new_i 
        j_difference = old_j - new_j
        if i_difference == -2 and j_difference == 2: # if the cible position of the jump is bottom left 
            board[old_i + 1][old_j - 1] = "---" # the jumpy place will be empty (jumpy piece will be removed)

        elif i_difference == 2 and j_difference == 2: # if the cible position of the jump is top left 
            board[old_i - 1][old_j - 1] = "---"

        elif i_difference == 2 and j_difference == -2: # if the cible position of the jump is top right 
            board[old_i - 1][old_j + 1] = "---"

        elif i_difference == -2 and j_difference == -2: # if the cible position of the jump is bottom right 
            board[old_i + 1][old_j + 1] = "---"

        if new_i == queen_row: # if the cible position of the player or computer is the index (0 or 7), then the player or computer become king
            letter = big_letter
        board[old_i][old_j] = "---" # if current player do a jump, the start position of the piece will be empty 
        board[new_i][new_j] = letter + str(new_i) + str(new_j) # if the current player does a jump, the cible position of the piece will receive the moved piece 

    def play(self, fromInd, toInd, mandatory_jumping): 
        """
        play() function is used to get the player move from appController and set it in the checker algorithm and get the computer moves (if available get the piece, that be jumped)
        :param: fromInd: start position of player piece
        :param: toInd: cible position of player piece
        :pram: mandatory_jumping: option to use mandatory jump or not for both player 


        :return: move1: x-coordinate of the start position of the computer piece, that be moved
                 move2: y-coordinate of the start position of the computer piece, that be moved
                 move3: x-coordinate of the cible position of the computer piece.
                 move4: y-coordinate of the cible position of the computer piece.
                 viaPiece: if available, the position of the player piece, that has been jumped
                 self.matrix: array list of the curent gameboard
        """
        viaPiece = [] # array of the list of the position of the piece, that has been jumped
        self.mandatory_jumping = mandatory_jumping 
        matrixFrom = self.matrix # copy the array of curent state of gameboard from controller to matrixFrom 
        if self.player_turn is True: # verify if player turn
            self.message = "Player's turn."
            self.observerController.notifyObserverViewCheckers(message = self.message) # notify the appController, that the player's turn
            _thread.start_new_thread(self.observerController.doAudio, ("Player's turn!",))
            
            verify = self.get_player_input(fromInd, toInd) # transfer the player's moves to (fromInd: start position of game piece and toInd: cible position of game piece)  
            if verify == True: # if the move of player is authorized
                self.player_turn = not self.player_turn # computer's turn 
                self.message = "Computer's turn. (Thinking...)"
                _thread.start_new_thread(self.observerController.doAudio, ("Computer's turn!",)) 
                self.observerController.notifyObserverViewCheckers(message = self.message)# notify the appController, that the computer's turn
                move1, move2, move3, move4 = self.evaluate_states() # get computer move 
                matrixTo = self.matrix # copy the current matrix after the computer has done a move

                indexs1 = np.flatnonzero(np.char.startswith(matrixFrom, 'b')) # get array of all index position of player piece of Previous Array
                indexs2 = np.flatnonzero(np.char.startswith(matrixTo, 'b')) # get  array of all index position of player piece after that the computer has done a move

                # compare both indexs to get the player piece that has been jumped 
                if (len(indexs1) != len(indexs2)): # if both index are not egal
                    arraydiffer = np.setdiff1d(matrixFrom, matrixTo) # get the  difference of two arrays and return the unique values in matrixFrom that are not in matrixTo.
                    indexs = np.flatnonzero(np.char.startswith(arraydiffer, 'b')) # get array of index of a value that begint with "b" (jumped player piece)
                    for i in indexs:
                        viaPiece.append(str(arraydiffer[i])[1:]) # get x,y index coordinate position of the jumped player piece and save it into array viaPiece

                self.player_turn = not self.player_turn # player turn

                if self.player_pieces == 1: # if  player has not pieces available, then computer win the game 
                    self.message = "You have no pieces left. :( :( :( YOU LOSE! ): ): ):"
                    self.final_score[1] += 1
                    time.sleep(3)
                    self.observerController.notifyObserverViewCheckers(newScore=self.final_score, message = self.message)
                    self.observerController.playAudio(GAMEOVER)
                    self.observerController.doAudio(WIN_FRANKA)

                elif self.computer_pieces == 1: # if  computer has not pieces available, then player win the game 
                    self.message =  "Computer has no pieces left. :) :) :) YOU WIN! (: (: (:"
                    self.final_score[0] += 1
                    time.sleep(3)
                    self.observerController.notifyObserverViewCheckers(newScore=self.final_score, message = self.message)
                    _thread.start_new_thread(self.observerController.playAudio, (GAMEWIN,))
                    _thread.start_new_thread(self.observerController.doAudio, (WIN_PLAYER,))


                coord1 = fromInd 
                coord2 = toInd
                old = coord1.split(",") 
                new = coord2.split(",") 

                old_i = old[0] 
                old_j = old[1]
                new_i = new[0]
                new_j = new[1]
                logger.debug("Checkers: Player play from b{}{} to b{}{}".format(old_i, old_j, new_i, new_j))
                logger.debug("Checkers: computer play from b{}{} to b{}{}".format (move1, move2, move3, move4))
                return move1, move2, move3, move4, viaPiece, self.matrix
            