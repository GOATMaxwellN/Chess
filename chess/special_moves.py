from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget
from squares import Squares

class Castle:

    wRook0 = None
    wRook1 = None
    bRook0 = None
    bRook1 = None

    wRook0Move = ["a1", "d1"]
    wRook1Move = ["h1", "f1"]

    bRook0Move = ["a8", "d8"]
    bRook1Move = ["h8", "f8"]

    @classmethod
    def setWhiteRook(cls, wRook):
        if wRook.name == "wRook0":
            cls.wRook0 = wRook
        else:
            cls.wRook1 = wRook

    @classmethod
    def setBlackRook(cls, bRook):
        if bRook.name == "bRook0":
            cls.bRook0 = bRook
        else:
            cls.bRook1 = bRook

    @classmethod
    def getMoveName(cls, move):
        if move == cls.wRook0Move or move == cls.bRook0Move:
            return "O-O-O"
        else:
            return "O-O"

    @classmethod
    def canCastle(cls, king):
        moves = []

        squares = Squares.getSquares()
        if king.isWhite:
            kingCoord = king.square.getCoord()
            # Check if king can castle queenside
            if not cls.wRook0.moved:  # If rook hasn't moved
                for i in range(1, 4):
                    sq = squares[kingCoord[0]-i][kingCoord[1]]
                    if sq.hasPiece() or (not king.canMoveTo(sq)):
                        break
                else:
                    moves.append(squares[2][0])  # square on 'c1'

            # Check if king can castle kingside
            if not cls.wRook1.moved:  # If rook hasn't moved
                for i in range(1, 3):
                    sq = squares[kingCoord[0]+i][kingCoord[1]]
                    if sq.hasPiece() or (not king.canMoveTo(sq)):
                        break
                else:
                    moves.append(squares[6][0])  # square on 'g1'
        else:
            kingCoord = king.square.getCoord()
            # Check if king can castle queenside
            if not cls.bRook0.moved:  # If rook hasn't moved
                for i in range(1, 4):
                    sq = squares[kingCoord[0]-i][kingCoord[1]]
                    if sq.hasPiece() or (not king.canMoveTo(sq)):
                        break
                else:
                    moves.append(squares[2][7])  # square on 'c8'

            # Check if king can castle kingside
            if not cls.bRook1.moved:  # If rook hasn't moved
                for i in range(1, 3):
                    sq = squares[kingCoord[0]+i][kingCoord[1]]
                    if sq.hasPiece() or (not king.canMoveTo(sq)):
                        break
                else:
                    moves.append(squares[6][7])  # square on 'g8'

        return moves


class EnPassant:

    canTakeEnPassant: list = []
    take = None
    move = None
    resetOnWhiteTurn = False

    @classmethod
    def potentialEnPassant(cls, square, isWhite):
        squares = Squares.getSquares()
        coord = square.getCoord()
        cls.take = square
        if isWhite:
            cls.resetOnWhiteTurn = False
        else:
            cls.resetOnWhiteTurn = True
        
        # coordinates for square to the left
        coordL = coord[0] - 1, coord[1]
        # coordinates for square to the right
        coordR = coord[0] + 1, coord[1]
        # square to take on
        if isWhite:
            coordM = coord[0], coord[1] - 1
        else:
            coordM = coord[0], coord[1] + 1
        cls.move = squares[coordM[0]][coordM[1]]

        if coord[0] == 0:
            cls.canTakeEnPassant.append(squares[coordR[0]][coordR[1]])
        elif coord[0] == 7:
            cls.canTakeEnPassant.append(squares[coordL[0]][coordL[1]])
        else:
            cls.canTakeEnPassant.append(squares[coordR[0]][coordR[1]])
            cls.canTakeEnPassant.append(squares[coordL[0]][coordL[1]])
    
    @classmethod
    def reset(cls, turn):
        """En passant only available in the immediate turn, so if en
        passant was available and en passant was available, it is
        removed."""
        if turn is cls.resetOnWhiteTurn:
            cls.canTakeEnPassant = []
            cls.move = None


class Promotion():

    @classmethod
    def getPromotionDialog(cls, isWhite, promoteToFunc):
        dialog = QWidget()
        layout = QHBoxLayout()

        queenButton = QPushButton()
        rookButton = QPushButton()
        knightButton = QPushButton()
        bishopButton = QPushButton()

        queenButton.clicked.connect(lambda: promoteToFunc("Queen"))
        rookButton.clicked.connect(lambda: promoteToFunc("Rook"))
        knightButton.clicked.connect(lambda: promoteToFunc("Knight"))
        bishopButton.clicked.connect(lambda: promoteToFunc("Bishop"))

        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        queenButton.setSizePolicy(sizePolicy)
        rookButton.setSizePolicy(sizePolicy)
        knightButton.setSizePolicy(sizePolicy)
        bishopButton.setSizePolicy(sizePolicy)

        layout.addWidget(queenButton)
        layout.addWidget(rookButton)
        layout.addWidget(knightButton)
        layout.addWidget(bishopButton)

        dialog.setLayout(layout)

        iconSize = QSize(100, 100)
        queenButton.setIconSize(iconSize)
        rookButton.setIconSize(iconSize)
        knightButton.setIconSize(iconSize)
        bishopButton.setIconSize(iconSize)

        if isWhite:
            queenButton.setIcon(QIcon(":pieces\\wQueen"))
            rookButton.setIcon(QIcon(":pieces\\wRook"))
            knightButton.setIcon(QIcon(":pieces\\wKnight"))
            bishopButton.setIcon(QIcon(":pieces\\wBishop"))
        else:
            queenButton.setIcon(QIcon(":pieces\\bQueen"))
            rookButton.setIcon(QIcon(":pieces\\bRook"))
            knightButton.setIcon(QIcon(":pieces\\bKnight"))
            bishopButton.setIcon(QIcon(":pieces\\bBishop"))

        return dialog