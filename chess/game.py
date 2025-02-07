import typing

from logging import getLogger

import logger
import pieces
from board import BoardView, Square
from interface import BoardToGameInterface
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from special_moves import Castle, EnPassant
from squares import Squares

stdlogger = getLogger(__name__)

class ChessGame(QWidget):
    
    def __init__(
            self,
            light_square_color: QColor,
            dark_square_color: QColor
            ):
        super().__init__()

        BoardToGameInterface.setCurrentGame(self)

        # Widgets
        self.board = BoardView(
            light_color=light_square_color,
            dark_color=dark_square_color
        )
        self.gameInfo = GameInfo()
        
        # Game variables
        self.turn = 0
        self.whiteTurn = True
        self.selectedPiece: pieces.Piece | None = None
        self.selectedSquare = None  # square of the selected piece
        self.wKing = None
        self.bKing = None

        # Make a board state
        self.squares: list[list[GameSquare]] = [[], [], [], [], [], [], [], []]
        Squares.setSquares(self.squares)
        self.pieces: list = []
        self.initializeBoardState()

        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(self.board, stretch=3)
        layout.addWidget(self.gameInfo, stretch=1)
        self.setLayout(layout)

    def initializeBoardState(self):
        """Initializes the board state by creating all the squares
        and adding the appropriate Pieces to their initial squares."""
        for i in range(8):
            for j in range(8):
                sqName = self.coordToSquareName((i, j))
                self.squares[i].append(GameSquare((i, j), sqName))

        for i in range(8):
            # Piece instances save themselves as an attribute to
            # the passed in 'square' using square.setPiece(self).

            # Add pawns
            p1 = pieces.Pawn(isWhite=True, square=self.squares[i][1])
            p2 = pieces.Pawn(isWhite=False, square=self.squares[i][6])
            self.pieces.extend((p1, p2))

            # Add rooks
            if i == 0 or i == 7:  # i=0 is the a file and i=7 is the h file
                p1 = pieces.Rook(isWhite=True, square=self.squares[i][0])
                p2 = pieces.Rook(isWhite=False, square=self.squares[i][7])
                self.pieces.extend((p1, p2))

            # Add knights
            if i == 1 or i == 6:
                p1 = pieces.Knight(isWhite=True, square=self.squares[i][0])
                p2 = pieces.Knight(isWhite=False, square=self.squares[i][7])
                self.pieces.extend((p1, p2))

            # Add bishops
            if i == 2 or i == 5:
                p1 = pieces.Bishop(isWhite=True, square=self.squares[i][0])
                p2 = pieces.Bishop(isWhite=False, square=self.squares[i][7])
                self.pieces.extend((p1, p2))

            # Add queens
            if i == 3:
                p1 = pieces.Queen(isWhite=True, square=self.squares[i][0])
                p2 = pieces.Queen(isWhite=False, square=self.squares[i][7])
                self.pieces.extend((p1, p2))

            # Add kings
            if i == 4:
                self.wKing = pieces.King(isWhite=True, square=self.squares[i][0])
                self.bKing = pieces.King(isWhite=False, square=self.squares[i][7])
                self.pieces.extend((self.wKing, self.bKing))

        for piece in self.pieces:
            piece.updateSquares(init=True)
        logger.showBoard(self.squares)

    def squareNameToCoord(self, squareName):
        """Convert a square's name (eg. a1) to indexes for the square
        on self.squares"""
        letters = "abcdefgh"

        letterCoord = letters.index(squareName[0])
        numCoord = int(squareName[1]) - 1

        return letterCoord, numCoord

    def coordToSquareName(self, coord):
        """Convert a square's index in self.squares (nicknamed coords),
        to the traditional square names in chess (eg. a1, b2)"""
        letters = "abcdefgh"

        sqName = letters[coord[0]] + str(coord[1] + 1)
        return sqName

    def pawnPromoted(self, promotedTo):
        """When user selects a piece for the promoting pawn to promote
        to."""
        if promotedTo[0] == "w":
            isWhite = True
        else:
            isWhite = False
        
        if promotedTo[1:] == "Queen":
            newPiece = pieces.Queen(
                isWhite=isWhite, square=self.promotionSquares[1], promotion=True
            )
        elif promotedTo[1:] == "Rook":
            newPiece = pieces.Rook(
                isWhite=isWhite, square=self.promotionSquares[1], promotion=True
            )
        elif promotedTo[1:] == "Knight":
            newPiece = pieces.Knight(
                isWhite=isWhite, square=self.promotionSquares[1], promotion=True
            )
        elif promotedTo[1:] == "Bishop":
            newPiece = pieces.Bishop(
                isWhite=isWhite, square=self.promotionSquares[1], promotion=True
            )

        turn = self.whiteTurn
        self.nextTurn()
        # Checks if a king is checked and whether it is checkmate
        # or not.
        checked = self.check()
        self.gameInfo.moveList.addMove(
            self.createMoveName(
                self.promotionSquares[0], self.promotionSquares[1], 
                promotingTo=promotedTo, capture=self.promotionOnCapture,
                **checked
            ),
            turn
        )

        self.promotionSquares = None


    def squareClicked(self, squareName: str):
        """""" 
        coord = self.squareNameToCoord(squareName)
        sq: Square = self.squares[coord[0]][coord[1]]
        piece = sq.getPiece()
        stdlogger.debug(f"Square at {squareName} has piece {piece}")


        if sq.hasPiece():
            stdlogger.debug(f"Square {coord} has piece.")
            # If there is a selected piece, and this square has an enemy piece,
            # check if it can move to this square and capture.
            if (self.selectedPiece is not None
                    and self.selectedPiece.isOppositeColorAs(piece)
                    and self.selectedPiece.canMoveTo(sq)
                ):

                moveType = self.selectedPiece.setSquare(sq)
                old_sq = self.selectedSquare
                turn = self.whiteTurn

                if moveType == "promotion":
                    self.promotionSquares = (old_sq, sq)
                    self.promotionOnCapture = True
                    return {
                        "action": "showPromotionDialog",
                        "state": (str(old_sq), str(sq), turn)
                    }
                
                self.nextTurn()
                # Checks if a king is checked and whether it is checkmate
                # or not.
                checked = self.check()
                self.gameInfo.moveList.addMove(
                    self.createMoveName(old_sq, sq, capture=True, **checked),
                    turn
                )

                return {
                    "action": "movePiece",
                    "squares": [str(old_sq), str(sq)]
                }

            # If there is a piece on the clicked square, check if it is
            # its color's turn. If so, select the piece and visually
            # highlight where it can go. If not, unhighlight any
            # highlighted squares, if any.
            if sq.getPiece().isWhite is not self.whiteTurn:
                return {"action": "unhighlightSquares"}
                
            self.selectedPiece = sq.getPiece()
            self.selectedSquare = sq
            return {
                "action": "highlightSquares",
                "squares": self.selectedPiece.getMoves(nameOnly=True)
            }
        else:
            # If there is no piece, check if there is a piece selected
            # that can move to the square.
            if (self.selectedPiece is not None 
                    and self.selectedPiece.canMoveTo(sq)):
                moveType = self.selectedPiece.setSquare(sq) # Moves the piece to sq
                old_sq = self.selectedSquare
                turn = self.whiteTurn
                EnPassant.reset(turn)  # if enPassant was available, remove it
                
                if moveType == "promotion":
                    self.promotionSquares = (old_sq, sq)
                    self.promotionOnCapture = False
                    return {
                        "action": "showPromotionDialog",
                        "state": (str(old_sq), str(sq), turn)
                    }
                
                self.nextTurn()
                
                checked = self.check()

                if moveType[0] == "normal":
                    self.gameInfo.moveList.addMove(
                        self.createMoveName(old_sq, sq, capture=False, **checked),
                        turn
                    )
                    return {
                        "action": "movePiece",
                        "squares": [str(old_sq), str(sq)]
                    }

                elif moveType[0] == "castle":
                    self.gameInfo.moveList.addMove(
                        self.createMoveName(old_sq, sq, capture=False, castle=moveType[1]),
                        turn
                    )
                    return {
                        "action": "castle",
                        "kingMove": [str(old_sq), str(sq)],
                        "rookMove": moveType[1]
                    }

                elif moveType[0] == "enPassant":
                    self.gameInfo.moveList.addMove(
                        self.createMoveName(old_sq, sq, capture=True),
                        turn
                    )
                    return {
                        "action": "enPassant",
                        "squares": [str(old_sq), str(sq)],
                        "take": str(EnPassant.take)
                    }
            else:
                # This can run if there is no selected piece or the
                # selected piece cannot move to the selected square.
                # Just unhighlight any highlighted squares, if any.
                return {"action": "unhighlightSquares"}

    def nextTurn(self):
            # After every turn, one of the kings will have their squares
            # updated, as they could be restricted at any time and their
            # trackedSquares list is not enough to keep up.
            if self.whiteTurn:
                self.bKing.updateSquares()
            else:
                self.wKing.updateSquares()

            self.selectedPiece = None
            self.selectedSquare = None

            self.whiteTurn = True if self.whiteTurn is False else False  # switch turns

            logger.showBoard(self.squares)

    def check(self):
        """Checks whether a king is checked and whether it is checkmate or not"""
        noCheck = {"check": False, "mate": False}
        checkNoMate = {"check": True, "mate": False}
        checkmate = {"check": True, "mate": True}

        # TODO: follow DRY
        if self.wKing.isChecked():
            # If king has no moves, check if a piece can block or capture the check
            if not self.wKing.getMoves():
                for piece in self.pieces:
                    if piece.isSameColorAs(self.wKing) and piece.getMoves():
                        return checkNoMate
                # Game over
                print("Black wins")
                return checkmate
            return checkNoMate

        elif self.bKing.isChecked():
            if not self.bKing.getMoves():
                for piece in self.pieces:
                    if piece.isSameColorAs(self.bKing) and piece.getMoves():
                        return checkNoMate
                # Game over
                print("White wins")
                return checkmate
            return checkNoMate
        
        return noCheck

    def createMoveName(self, oldSquare, newSquare, capture = False, check = False,
                       mate = False, castle = None, promotingTo = None):
        """Creates a move name (eg. Nf3) from looking at a pieces'
        current square (oldSquare) and the square it's going to move
        to (newSquare)"""

        def getAbbr(name):
            # Abbreviation for knight in moves is N, as the King takes K
            if (name) == "Knight":
                return "N"
            elif name == "Pawn" and capture:
                return str(oldSquare)[0]
            elif name == "Pawn":
                return ""
            else:
                return name[0]

        if castle:
            return Castle.getMoveName(castle)

        pieceName = newSquare.getPiece().pieceName
        if promotingTo is None:
            prefix = getAbbr(pieceName)
        else:
            prefix = getAbbr("Pawn")

        suffix = ""
        if capture:
            prefix += 'x'
        if promotingTo is not None:
            suffix += '=' + getAbbr(promotingTo[1:])
        if mate:
            suffix += '#'
        elif check:
            suffix += '+'

        return prefix + str(newSquare) + suffix


class GameInfo(QFrame):

    def __init__(self):
        super().__init__()
        self.moveList = MoveList()

        layout = QVBoxLayout()
        layout.addWidget(self.moveList, stretch=1)
        self.setLayout(layout)


class MoveList(QFrame):
    """Widget that shows move history of a game"""

    def __init__(self, move_log: typing.Optional[list[tuple[str, str]]]=None):
        """
        Parameters
        ----------
        move_log: list of tuples[str, str] (optional)
            History of moves, each element of which is pair of White's and Black's moves.
            Defaults to empty.
        """
        super().__init__()
        _move_log = move_log if move_log is not None else []
        self.move_log = _move_log
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
        self.setLineWidth(3)

        # Row number for the move list (increments after black's turn)
        self.row = 0

        label = QLabel("Moves")
        self.moveList, self.moveListLayout = self.createMoveList()

        layout = QVBoxLayout()
        layout.addWidget(label, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.moveList, stretch=9)
        self.setLayout(layout)
        for move_pair in _move_log:
            for move, is_white in zip(move_pair, (True, False)):
                self.addMove(move, is_white)

    def createMoveList(self):
        """Creates frame that will hold move history"""
        moveList = QFrame()
        layout = QGridLayout()
        for i in range(20):
            layout.setRowStretch(i, 1)
        layout.setColumnStretch(0, 1)  # Column showing turn number should be smaller.
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 2)
        moveList.setLayout(layout)
        return moveList, layout

    def addMove(self, move: str, isWhite=True):
        """Adds move to the move history"""
        turnLabel = QLabel(str(self.row + 1))
        label = QLabel(move)
        if isWhite:
            self.moveListLayout.addWidget(turnLabel, self.row, 0)
            self.moveListLayout.addWidget(label, self.row, 1)
            self.move_log.append((move, "..."))
        else:
            self.moveListLayout.addWidget(label, self.row, 2)
            self.row += 1
            self.move_log[-1] = (self.move_log[-1][0], move)

class GameSquare:
    """A detailed representation of a square that will hold
    info about the square's state"""

    def __init__(self, coord, name):
        self.name = name
        self.piece = None
        self.trackedBy = []
        self.controlledBy = []
        self.pinned = False
        self.coord = coord

    def setPiece(self, piece, init=False):
        """Sets a piece to this square. If there was already a piece,
        and the piece param is not None, the piece on this square is 
        captured and their getCaptured() method is called."""
        if (self.piece is not None) and (piece is not None):
            self.piece.getCaptured()

        self.piece = piece
        # Don't update squares when initializing the pieces on their
        # initial positions
        if (not init) and (piece is not None):
            self.piece.updateSquares()

    def addTrackingPiece(self, piece):
        self.trackedBy.append(piece)

    def removeTrackingPiece(self, piece):
        indexToRemove = self.trackedBy.index(piece)
        del self.trackedBy[indexToRemove]

    def getTrackingPieces(self):
        return self.trackedBy

    def addControllingPiece(self, piece):
        self.controlledBy.append(piece)
    
    def getControllingPieces(self):
        return self.controlledBy
    
    def removeControllingPiece(self, piece):
        indexToRemove = self.controlledBy.index(piece)
        del self.controlledBy[indexToRemove]

    def isControlledByOppositeColor(self, piece):
        for controllingPiece in self.controlledBy:
            if controllingPiece.isOppositeColorAs(piece):
                return True
        return False

    def getCoord(self):
        return self.coord

    def hasPiece(self):
        if self.piece is not None:
            return True
        return False

    def getPiece(self):
        return self.piece

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name