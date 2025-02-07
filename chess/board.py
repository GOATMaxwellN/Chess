"""This module handles the drawing of the board and its pieces."""
from __future__ import annotations

import os
from logging import getLogger

import resources

from interface import BoardToGameInterface
from pieces import Piece

from PySide6.QtCore import QPointF, QRectF, QSize, QSizeF, Qt
from PySide6.QtGui import QBrush, QColor, QPixmap
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
)
from special_moves import Promotion


logger = getLogger(__name__)

# Create a list with the names of each square starting from
# [a8, b8, ..., h8, a7, b7, ..., h7, etc..]
SQUARE_NAMES = [(l+n) for n in "87654321" for l in "abcdefgh"]


class BoardView(QGraphicsView):

    VIEW_SIZE = QSize(600, 600)

    def __init__(
        self,
        light_color: QColor,
        dark_color: QColor
        ):
        super().__init__()
        self.setGeometry(
            0, 0, self.VIEW_SIZE.width(), self.VIEW_SIZE.height())
        self.setMinimumSize(self.VIEW_SIZE)

        scene = BoardScene(
            light_color=light_color,
            dark_color=dark_color
        )
        self.setScene(scene)


class BoardScene(QGraphicsScene):

    # Make a little smaller than the view for some margins
    SCENE_SIZE = QSize(555, 555)
    SQUARE_SIZE: QSize = SCENE_SIZE / 8 # type: ignore
    PIECE_SIZE = SQUARE_SIZE - QSize(10, 10) # type: ignore

    INITIAL_POS = {
        "wRook": ("a1", "h1"),
        "wKnight": ("b1", "g1"),
        "wBishop": ("c1", "f1"),
        "wQueen": ("d1",),
        "wKing": ("e1",),
        "wPawn": ("a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2"),
        "bRook": ("a8", "h8"),
        "bKnight": ("b8", "g8"),
        "bBishop": ("c8", "f8"),
        "bQueen": ("d8",),
        "bKing": ("e8",),
        "bPawn": ("a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7"),
    }

    def __init__(
            self, 
            light_color,
            dark_color
        ):
        super().__init__()
        self.setSceneRect(
            5, 5, self.SCENE_SIZE.width(), self.SCENE_SIZE.height())

        # Create the squares.
        self.squares = self.createSquares(
            light_color=light_color,
            dark_color=dark_color
        )
        # Draw the board
        self.drawBoard()
        # Draw pieces on their initial position
        self.drawPiecesInInitialPos()

        # Util variables
        self.highlightedSquares = []

        self.promotionDialogShown = False

    def createSquares(
            self, 
            light_color: QColor,
            dark_color: QColor,
        ) -> dict[str, Square]:
        """Create Square objects for every square on the board and put
        them in a dictionary."""
        squares = {}
        squareNames = iter(SQUARE_NAMES)
        whiteOnEven = True
        # row height and col width are the same
        rowHeight = self.SQUARE_SIZE.height()
        rowCoord = [(x * rowHeight) for x in range(0, 8)]
        colCoord = [(y, y * rowHeight) for y in range(0, 8)]

        for row in rowCoord:
            # At each row, white squares will be on the even numbered cols
            # or the odd numbered cols. c is the variable that knows the
            # parity of a column
            whiteOnEven = False if whiteOnEven is True else True
            for c, col in colCoord:
                rect = QRectF(QPointF(col, row), self.SQUARE_SIZE)
                name = next(squareNames)

                if (c%2==0 and whiteOnEven) or (c%2==1 and not whiteOnEven):
                    squares[name] = Square(
                        rect=rect, color=light_color, name=name)
                else:
                    squares[name] = Square(
                        rect=rect, color=dark_color, name=name)

        return squares

    def drawBoard(self):
        "Draws all the Square objects to make a chess board"
        for sq in self.squares:
            self.addItem(self.squares[sq])

    def drawPiecesInInitialPos(self):
        """Draw the pieces in their initial positions"""
        # These ids are appened to the piece's name so that they're unique
        for piece in self.INITIAL_POS:
            img = QPixmap(f":pieces{os.path.sep}{piece}").scaled(
                self.PIECE_SIZE,
                Qt.KeepAspectRatio
                )
            for id_, pos in enumerate(self.INITIAL_POS[piece]):
                imgItem = self.addPixmap(img)
                sq = self.squares[pos]
                sq.setPiece(piece + str(id_), imgItem)

    def highlightSquares(self, squares):
        """Change color of selected squares to highlight them"""
        # First unhighlight previously selected squares, if any
        self.unhighlightSquares()

        # Highlight selected squares
        for sqName in squares:
            sq = self.squares[sqName]
            self.highlightedSquares.append((sq, sq.brush()))
            sq.setBrush(Qt.yellow)

    def unhighlightSquares(self):
        """Unhighlight currently highlighted squares"""
        for sq, brush in self.highlightedSquares:
            sq.setBrush(brush)
        self.highlightedSquares.clear()

    def movePiece(self, squares):
        """Move piece from squares[0] to squares[1]"""
        from_sq, to_sq = self.squares[squares[0]], self.squares[squares[1]]
        logger.debug(f"Moving {from_sq.getPiece()} from {str(from_sq)} to {str(to_sq)}")
        from_sq.movePieceTo(to_sq)

        self.unhighlightSquares()

    def removePiece(self, square):
        sq = self.squares[square]
        self.removeItem(sq.getPiecePixmap())
        sq.setPiece(None, None)

    def showPromotionDialog(self, state):
        """When a pawn reaches the 1st or 8th rank, this shows a screen
        that lets the user pick what piece they want to promote the
        pawn to.
        
        state : tuple
            [0] square pawn moved from, [1] square pawn promoting on,
            [2] color of the pawn"""
        self.promotionDialogShown = True
        self.promotionDialog = self.addWidget(
            Promotion.getPromotionDialog(
                state[2], 
                lambda promoteTo: self.promotePawn(state, promoteTo)
            )
        )

        # Centers the dialog in the middle of the board
        x, y = self.promotionDialog.boundingRect().size().toTuple()
        center = self.sceneRect().center() - QPointF((1/2)*x, (1/2)*y)
        self.promotionDialog.setPos(center)

    def promotePawn(self, state, promoteTo):
        """Promotes a pawn to promoteTo"""
        self.promotionDialogShown = False
        self.removeItem(self.promotionDialog)

        old_sq, new_sq, whiteTurn = state
        from_sq, to_sq = self.squares[old_sq], self.squares[new_sq]
        if whiteTurn:
            promoteTo = "w" + promoteTo
        else:
            promoteTo = "b" + promoteTo

        from_sq.movePieceTo(to_sq, promotingTo=promoteTo)
        self.unhighlightSquares()

        BoardToGameInterface.pawnPromoted(promoteTo)

    def printSquares(self):
        """Prints all the squares and the pieces on each square.
        Used for debugging."""
        i = 1
        for name in self.squares:
            end = '\t' if i % 8 != 0 else '\n'
            piece = self.squares[name].getPiece()
            print(name + ': ' + str(self.squares[name].getPiece()), end=end)
            i += 1
        print('-' * 20)


class Square(QGraphicsRectItem):
    """This class inherits from QGraphicsRectItem, so it is used to
    draw a square on the board scene. Keeps track of the name of any
    piece that is on it and has mouse events to handle when the user
    clicks it."""

    def __init__(self, rect: QRectF, color: QColor, name):
        super().__init__(rect)
        self.name = name
        self.piece: None | str = None
        self.piecePixmap: None | QGraphicsPixmapItem = None

        # Set color of the square
        self.setBrush(QBrush(color))

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """When a square is clicked and there is a piece on that square,
        this function will highlight the squares that the piece can move
        to."""
        logger.debug(f"Received click on square")
        scene: BoardScene = self.scene() # type: ignore[assignment]
        # Don't let squares be clicked if there is a pawn promoting.
        if scene.promotionDialogShown:
            return super().mousePressEvent(event)
        # Let the game know this square has been clicked
        result = BoardToGameInterface.squareClicked(
            self.name)

        # Check result to know what to do
        if (action := result["action"]) == "highlightSquares":
            logger.debug(f"Highlighting squares: {result["squares"]}")
            scene.highlightSquares(result["squares"])
        elif action == "showPromotionDialog":
            logger.debug(f"Promotion")
            scene.showPromotionDialog(result["state"])
        elif action == "unhighlightSquares":
            logger.debug(f"Unighlighting squares")
        # below are moving actions
        elif (BoardToGameInterface.CURRENT_GAME.selectedPiece 
            and 
            not BoardToGameInterface.CURRENT_GAME.selectedPiece.canMoveTo(result["squares"][1])
            ):
            return super().mousePressEvent(event)
        elif action == "movePiece":
            logger.debug(f"Moving piece: {result["squares"]}")
            scene.movePiece(result["squares"])
            scene.unhighlightSquares()
        elif action == "castle":
            logger.debug(f"Castling")
            scene.movePiece(result["kingMove"])
            scene.movePiece(result["rookMove"])
        elif action == "enPassant":
            logger.debug(f"En passant")
            scene.movePiece(result["squares"])
            scene.removePiece(result["take"])

        return super().mousePressEvent(event)

    def setPiece(self, piece: Piece | None, pixmap: QGraphicsPixmapItem | None):
        """Sets a piece to this square. Has the effect of visually moving
        the piece to this square on the board."""
        # Must come first, as it checks the current value of self.piece
        self.setPiecePixmap(pixmap, align_center=True)

        self.piece = piece

    def getPiece(self):
        return self.piece

    def movePieceTo(self, square_to: Square, promotingTo=None):
        """Moves the piece on this square to another square"""
        piece, pixmap = self.piece, self.piecePixmap
        self.piece = self.piecePixmap = None

        if promotingTo is not None:
            assert pixmap is not None
            self.scene().removeItem(pixmap)  # remove pawn

            newPixmap = self.scene().addPixmap(QPixmap(f":pieces{os.path.sep}{promotingTo}"))
            square_to.setPiece(promotingTo, newPixmap)
            return
        
        square_to.setPiece(piece, pixmap)

    def setPiecePixmap(
        self,
        pixmap: QGraphicsPixmapItem | None,
        align_center=False
        ):
        """Gives a reference to the square of the pixmap item of the piece
        on this square."""

        def sizef_to_pointf(size: QSizeF):
            return QPointF(size.height(), size.width())
        if pixmap is None:
            self.piecePixmap = None
            
        if self.hasPiece():
            # If there was a piece on this square, it was captured
            # and its pixmap can be deleted off the scene
            assert self.piecePixmap is not None
            self.scene().removeItem(self.piecePixmap)
        move_to = self.getCoord()
        assert pixmap is not None
        if align_center:
            square_size = sizef_to_pointf(self.rect().size())
            pixmap_size = sizef_to_pointf(pixmap.boundingRect().size())
            move_to += (square_size - pixmap_size) * 0.5 
        pixmap.setOffset(move_to)  # moves img of piece to sq

        self.piecePixmap = pixmap

    def getPiecePixmap(self):
        return self.piecePixmap

    def getCoord(self):
        return self.rect().topLeft()

    def getCenter(self):
        return self.rect().center()

    def hasPiece(self):
        if self.piece is None:
            return False
        return True
