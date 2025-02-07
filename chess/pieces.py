"""This module defines classes for every type of chess piece"""
from logging import getLogger

import logger
from interface import BoardToGameInterface
from special_moves import Castle, EnPassant
from squares import Squares

stdlogger = getLogger(__name__)

class Piece():
    """Base class for all pieces"""

    def __init__(self, isWhite, square):
        pieceType = type(self)
        if isWhite:
            self.name = "w" + pieceType.pieceName + str(pieceType.w_id)
            pieceType.w_id += 1
        else:
            self.name = "b" + pieceType.pieceName + str(pieceType.b_id)
            pieceType.b_id += 1

        self.isWhite = isWhite
        self.trackedSquares = []
        self.moves = []
        self.nonMovesControlledSquares = []
        self.pinning = None
        self.pinnedTo = []
        self.captured = False

        # Adds itself to a square, which starts things off
        self.square = square
        self.square.setPiece(self, init=True)

    def getCaptured(self):
        """Sets this piece's captured attribute to True. Means that this
        piece no longer exists on the board."""
        self.clearTrackedAndControlledSquares()
        if self.pinning is not None:
            self.unpinPiece()
        self.captured = True

    def addTrackedSquare(self, square):
        self.trackedSquares.append(square)
        square.addTrackingPiece(self)

    def addNonMoveControlledSquare(self, square):
        self.nonMovesControlledSquares.append(square)
        square.addControllingPiece(self)

    def setSquare(self, square):
        """Sets a square to this piece. Called when this piece moves to
        another square"""
        # Clear tracked squares so piece won't appear on newSquareTrackers
        self.clearTrackedAndControlledSquares()
        old_square = self.square  # save old square
        old_square.setPiece(None)  # remove itself from old square
        self.square = square  # update square
        
        # Get all pieces that could be affected by the move
        oldSquareTrackers = set(old_square.getTrackingPieces())
        newSquareTrackers = set(self.square.getTrackingPieces())
        piecesToUpdate = oldSquareTrackers.union(newSquareTrackers)

        # Move piece to new square and update it
        # Must be moved after the trackers have been obtained but before
        # they are updated, so as to avoid common edge cases.
        self.square.setPiece(self)
        self.uncheckKing()
        
        # Update the pieces affected by the move
        logger.pieceMoved(self, piecesToUpdate)  # Marks the start
        for piece in piecesToUpdate:
            piece.updateSquares()
        logger.pieceMoved(self)  # Marks the end of the updates

        return "normal",


    def updateSquares(self, init=False):
        """This function should be reimplemented to update the squares of
        this piece. This only serves to log the changes."""
        if not init:
            logger.pieceUpdatedSquares(self)

    def linearUpdateSquares(self, init=False):
        """updateSquares() implementation for Bishops, Rooks and Queens.
        Their move generation and ability to pin is all the same, and
        they move in a 'linear' fashion."""
        if self.captured:
            return

        self.clearTrackedAndControlledSquares()
        if self.pinning is not None:  # If pinning a piece, unpin it
            self.unpinPiece()

        coord = self.square.getCoord()
        squares = Squares.getSquares()

        for d in self.directions:
            canAddToMoves = True
            piecesOnRankOrFile = []
            for i in range(1, 8):
                sqCoords = coord[0] + d[0]*i, coord[1] + d[1]*i
                if (sqCoords[0] == 8 or sqCoords[1] == 8  # End of file or rank 
                    or sqCoords[0] == -1 or sqCoords[1] == -1):  # No negs
                    break

                sq = squares[sqCoords[0]][sqCoords[1]]
                piece = sq.getPiece()
                
                # Update Piece and Square's control vars
                self.addTrackedSquare(sq)

                # Everything that needs to happen if there is a piece
                if sq.hasPiece():

                    # Check if piece is a king. If piece is a king of 
                    # opposite color, determine if there is an enemy 
                    # piece in front of it that should be pinned.
                    if piece.pieceName == "King" and self.isOppositeColorAs(piece):
                        if (len(piecesOnRankOrFile) == 1
                                and (self.isOppositeColorAs(piecesOnRankOrFile[0]))):
                            self.pinPiece(piecesOnRankOrFile[0], d, sq)
                        elif len(piecesOnRankOrFile) == 0:
                            self.checkKing(piece, d)
                        
                    # Track pieces on the rank or file. Used to
                    # determine if a piece should be pinned if a
                    # king is encountered.
                    piecesOnRankOrFile.append(piece)
                
                    # If piece is of opposite color, add to moves list.
                    if canAddToMoves:
                        if self.isOppositeColorAs(piece):
                            self.addMove(sq)
                            canAddToMoves = False
                        else:
                            self.addNonMoveControlledSquare(sq)
                            canAddToMoves = False
                else:
                    # Everything that needs to happen if there is no piece
                    if canAddToMoves:
                        self.addMove(sq)

        if not init:
            logger.pieceUpdatedSquares(self)

    def checkKing(self, kingPiece, dirOfCheck = None):
        """Checks the king"""
        squares = Squares.getSquares()
        coord = self.square.getCoord()
        kingSquare = kingPiece.square
        checkingSquares = [self.square]

        if dirOfCheck is not None:
            for i in range(8):
                sq_coord = coord[0] + dirOfCheck[0]*i, coord[1] + dirOfCheck[1]*i
                if sq_coord == kingSquare.getCoord():
                    break
                checkingSquares.append(squares[sq_coord[0]][sq_coord[1]])

        kingPiece.check(checkingSquares)

    def uncheckKing(self):
        """If the piece's king was in check pending the piece's move,
        remove the king from check since the move would remove them
        from check."""
        # checkingSquares would be an empty list if the king was
        # not in check
        if (self.isWhite and King.whiteCheckingSquares
                or (not self.isWhite) and King.blackCheckingSquares):
            King.checkedKing.uncheck()

    def clearTrackedAndControlledSquares(self):
        """Goes through a squares' trackedSquares list and removes the piece
        from their trackingPiece lists. Goes through a squares' controlledBy list
        and removes the piece from their controlledBy list. Also clears the piece's
        controlledSquares and moves list as they will be refreshed. This will be called
        whenever a piece is updating their squares due to a move."""
        for sq in self.trackedSquares:
            sq.removeTrackingPiece(self)
        for sq in self.moves:
            sq.removeControllingPiece(self)
        for sq in self.nonMovesControlledSquares:
            sq.removeControllingPiece(self)
        
        self.trackedSquares.clear()
        self.moves.clear()
        self.nonMovesControlledSquares.clear()

    def addMove(self, square, castle = False):
        """Adds square to moves list and adds the piece to the squares's
        controlledBy list."""
        # only for the kings
        if castle:
            self.castleMoves.clear()
            self.castleMoves.extend(square) # might be able to castle both sides
            return

        self.moves.append(square)
        square.addControllingPiece(self)

    def pinPiece(self, piece, direction, kingSquare):
        squares = Squares.getSquares()
        coord = self.square.getCoord()
        allowedSquares = [self.square]

        for i in range(8):
            sq_coord = coord[0] + direction[0]*i, coord[1] + direction[1]*i
            if sq_coord == kingSquare.getCoord():
                break
                
            allowedSquares.append(squares[sq_coord[0]][sq_coord[1]])

        piece.setPin(allowedSquares)
        self.pinning = piece

    def unpinPiece(self):
        self.pinning.removePin()
        self.pinning = None

    def setPin(self, allowedSquares):
        self.pinnedTo = allowedSquares

    def removePin(self):
        self.pinnedTo.clear()

    def isOppositeColorAs(self, piece):
        if self.isWhite is piece.isWhite:
            return False
        return True

    def isSameColorAs(self, piece):
        if self.isWhite is piece.isWhite:
            return True
        return False

    def __str__(self):
        toPrint = (f"{self.name} on square {self.square.name}\n"
                   f"Controlling: {self.trackedSquares}\n"
                   f"Pinned By: {self.pinnedTo}\n"
                   f"Moves: {self.moves}\n" + "-"*20)
        return toPrint

    def __repr__(self):
        return self.name

    def getMoves(self, nameOnly=False):
        
        if type(self) != King:
            if self.pinnedTo:
                moves = set(self.pinnedTo).intersection(set(self.moves))
            elif (King.whiteCheckingSquares is not None) and self.isWhite:
                moves = set(King.whiteCheckingSquares).intersection(set(self.moves))
            elif (King.blackCheckingSquares is not None) and (not self.isWhite):
                moves = set(King.blackCheckingSquares).intersection(set(self.moves))
            else:
                moves = self.moves
        else:
            moves = self.moves.copy()
            moves.extend(self.castleMoves)

        stdlogger.debug(f"Available moves for {repr(self)}: {list(map(str, moves))}")

        if nameOnly:
            # Square.__str__ simply returns the name of a square
            return [str(sq) for sq in moves]
        return moves

    def canMoveTo(self, square):
        """Checks if square is in this Piece's move list"""
        stdlogger.debug(f"{str(self)} can move to {str(square)}: {square in self.getMoves()}")
        return square in self.getMoves()


class King(Piece):
    w_id = 0
    b_id = 0
    pieceName = "King"

    # If the white or black king are checked, the checking squares the
    # direction in which a king is being checked.
    whiteCheckingSquares = None
    blackCheckingSquares = None
    checkedKing = None
    
    def __init__(self, isWhite, square):
        super().__init__(isWhite, square)
        self.checked = False
        self.moved = False
        self.castleMoves = []
        if self.isWhite:
            self.kingsideCastleSquare = "g1"
            self.queensideCastleSquare = "c1"
        else:
            self.kingsideCastleSquare = "g8"
            self.queensideCastleSquare = "c8"

    def isChecked(self):
        return self.checked

    def check(self, checkingSquares):
        """Called by an enemy piece when they check this king."""
        # If the king is already checked, there is a double check
        # and the king MUST move, there are no checking squares
        # to block.
        if self.checked:
            if self.isWhite:
                King.whiteCheckingSquares = []
            else:
                King.blackCheckingSquares = []
            return
            
        self.checked = True
        King.checkedKing = self
        if self.isWhite:
            King.whiteCheckingSquares = checkingSquares
        else:
            King.blackCheckingSquares = checkingSquares

    def uncheck(self):
        self.checked = False
        King.checkedKing = None
        if self.isWhite:
            King.whiteCheckingSquares = None
        else:
            King.blackCheckingSquares = None

    def setSquare(self, square):
        super().setSquare(square)
        moved_ = self.moved
        self.moved = True
        if not moved_:
            if self.isWhite:
                if str(square) == self.kingsideCastleSquare:
                    Castle.wRook1.setSquare(Squares.getSquares()[5][0])
                    return "castle", Castle.wRook1Move
                elif str(square) == self.queensideCastleSquare:
                    Castle.wRook0.setSquare(Squares.getSquares()[2][0])
                    return "castle", Castle.wRook0Move
            else:
                if str(square) == self.kingsideCastleSquare:
                    Castle.bRook1.setSquare(Squares.getSquares()[5][7])
                    return "castle", Castle.bRook1Move
                elif str(square) == self.queensideCastleSquare:
                    Castle.bRook0.setSquare(Squares.getSquares()[2][7])
                    return "castle", Castle.bRook0Move

        return "normal",


    def updateSquares(self, init=False):
        self.clearTrackedAndControlledSquares()
        if not self.moved:
            self.addMove(Castle.canCastle(self), castle=True)

        coord = self.square.getCoord()
        squares = Squares.getSquares()

        directions = (
            (1,0), (0, 1), (-1, 0), (0, -1),
            (1, 1), (1, -1), (-1, -1), (-1, 1))
        
        for d in directions:
            new_coord = coord[0] + d[0], coord[1] + d[1]
            if ((new_coord[0] > 7 or new_coord[1] > 7)
                    or (new_coord[0] < 0 or new_coord[1] < 0)):
                continue

            sq = squares[new_coord[0]][new_coord[1]]
            self.addTrackedSquare(sq)
            ctrledByOppColor = sq.isControlledByOppositeColor(self)

            if sq.hasPiece():
                if (self.isOppositeColorAs(sq.getPiece())
                        and (not ctrledByOppColor)):
                    self.addMove(sq)
                else:
                    self.addNonMoveControlledSquare(sq)
            else:
                if not ctrledByOppColor:
                    self.addMove(sq)
                else:
                    self.addNonMoveControlledSquare(sq)
                
        
        super().updateSquares(init=init)

    def canMoveTo(self, square):
        moves = set(self.moves).union(set(self.castleMoves))
        return square in moves


class Queen(Piece):
    w_id = 0
    b_id = 0
    pieceName = "Queen"
    
    def __init__(self, isWhite, square, promotion = False):
        super().__init__(isWhite, square)
        self.directions = (
            (1, 0), (0, -1), (-1, 0), (0, 1),
            (1, 1), (1, -1), (-1, -1), (-1, 1)
        )
        if promotion:
            self.updateSquares()

    def updateSquares(self, init=False):
        super().linearUpdateSquares(init)


class Pawn(Piece):
    w_id = 0
    b_id = 0
    pieceName = "Pawn"

    def __init__(self, isWhite, square):
        super().__init__(isWhite, square)
        self.controlledSquares = []

    def updateSquares(self, init=False):
        """Gets the squares this pawn can move to and updates the state
        of any squares that this pawn affects."""
        
        def addUpperAdjacentSquare():
            """Controls the two squares on the pawn's diagonals. Adds
            them to the moves list if there is an enemy piece"""
            self.addTrackedSquare(sq)
            self.controlledSquares.append(sq)
            sq.addControllingPiece(self)
            piece = sq.getPiece()
            if sq.hasPiece() and self.isOppositeColorAs(piece):
                if piece.pieceName == "King":
                    self.checkKing(piece)
                self.addMove(sq)

        if self.captured:
            return
        
        self.clearTrackedAndControlledSquares()
        coord = self.square.getCoord()
        squares = Squares.getSquares()

        self.updateMoves()

        if self.isWhite:
            if coord[0] != 0:
                sq = squares[coord[0]-1][coord[1]+1]
                addUpperAdjacentSquare()
            if coord[0] != 7:
                sq = squares[coord[0]+1][coord[1]+1]
                addUpperAdjacentSquare()
        else:
            if coord[0] != 0:
                sq = squares[coord[0]-1][coord[1]-1]
                addUpperAdjacentSquare()
            if coord[0] != 7:
                sq = squares[coord[0]+1][coord[1]-1]
                addUpperAdjacentSquare()

        super().updateSquares(init=init)

    def updateMoves(self):
        """Updates the possible squares this pawn can move to"""
        coord = self.square.getCoord()
        squares = Squares.getSquares()

        if self.isWhite:
            sq = squares[coord[0]][coord[1]+1]
            self.addTrackedSquare(sq)
            if not sq.hasPiece():
                self.addMove(sq)
                if coord[1] == 1:  # If pawn is still on 2nd rank
                    sq = squares[coord[0]][coord[1]+2]
                    self.addTrackedSquare(sq)

                    if not sq.hasPiece():
                        self.addMove(sq)
        else:
            sq = squares[coord[0]][coord[1]-1]
            self.addTrackedSquare(sq)
            if not sq.hasPiece():
                self.moves.append(sq)
                if coord[1] == 6:  # If pawn is still on 7th rank
                    sq = squares[coord[0]][coord[1]-2]
                    self.addTrackedSquare(sq)
                    if not sq.hasPiece():
                        self.moves.append(sq)

    def clearTrackedAndControlledSquares(self):
        for sq in self.trackedSquares:
            sq.removeTrackingPiece(self)
        for sq in self.controlledSquares:
            sq.removeControllingPiece(self)

        self.trackedSquares.clear()
        self.controlledSquares.clear()
        self.moves.clear()

    def addMove(self, square):
        # Adds move to Pawn's moves list without 'controlling' the square.
        # This is done because a Pawn always controls its two upper
        # adjacent squares. This function enables them to move there, but
        # the square is already 'controlled'.
        self.moves.append(square)

    def setSquare(self, square):
        if square.getCoord()[1] == 0 or square.getCoord()[1] == 7:
            self.clearTrackedAndControlledSquares()
            # Get pieces that tracked the square the pawn was on
            # and update them because the pawn is no longer there.
            trackingPieces = self.square.getTrackingPieces()
            self.square.setPiece(None)
            for piece in trackingPieces:
                piece.updateSquares()
            return "promotion"
        elif (self.square.getCoord()[1] == 1 or self.square.getCoord()[1] == 6
                and (square.getCoord()[1] == 3 or square.getCoord()[1] == 4)):
            EnPassant.potentialEnPassant(square, self.isWhite)
        elif square == EnPassant.move:
            EnPassant.take.setPiece(None)
            super().setSquare(square)
            return "enPassant", EnPassant.take

        return super().setSquare(square)

    
    def getMoves(self, nameOnly = False):
        if self.square in EnPassant.canTakeEnPassant:
            self.addMove(EnPassant.move)
        return super().getMoves(nameOnly)
    

class Rook(Piece):
    w_id = 0
    b_id = 0
    pieceName = "Rook"

    def __init__(self, isWhite, square, promotion = False):
        super().__init__(isWhite, square)
        # Add rook to Castle class to allow king to determine when it
        # can castle.
        if self.name[0:-1] == "wRook":
            Castle.setWhiteRook(self)
        elif self.name[0:-1] == "bRook":
            Castle.setBlackRook(self)
        
        self.directions = (
            (1, 0), (0, -1), (-1, 0), (0, 1)
        )
        self.moved = False
        if promotion:
            self.updateSquares()

    def updateSquares(self, init=False):
        super().linearUpdateSquares(init)

    def setSquare(self, square):
        self.moved = True
        return super().setSquare(square)


class Knight(Piece):
    w_id = 0
    b_id = 0
    pieceName = "Knight"  
    
    def __init__(self, isWhite, square, promotion = False):
        super().__init__(isWhite, square)
        if promotion:
            self.updateSquares()

    def updateSquares(self, init=False):
        if self.captured:
            return

        self.clearTrackedAndControlledSquares()
        coord = self.square.getCoord()
        squares = Squares.getSquares()

        direction = (
            (1, 2), (2, 1), (2, -1), (1, -2),
            (-1, -2), (-2, -1), (-2, 1), (-1, 2))
        
        for d in direction:
            new_coord = coord[0] + d[0], coord[1] + d[1]
            if ((new_coord[0] > 7 or new_coord[1] > 7)
                    or (new_coord[0] < 0 or new_coord[1] < 0)):
                continue

            sq = squares[new_coord[0]][new_coord[1]]
            piece = sq.getPiece()
            self.addTrackedSquare(sq)

            if sq.hasPiece():
                # Check if you're checking the enemy king
                if self.isOppositeColorAs(piece):
                    if piece.pieceName == "King":
                        self.checkKing(piece)
                    self.addMove(sq)
                else:
                    # If ally piece on this square, can't move there but
                    # still control the square.
                    self.addNonMoveControlledSquare(sq)
            else:
                self.addMove(sq)

        super().updateSquares(init=init)
    

class Bishop(Piece):
    w_id = 0
    b_id = 0
    pieceName = "Bishop"
    
    def __init__(self, isWhite, square, promotion = False):
        super().__init__(isWhite, square)
        self.directions = (
            (1, 1), (1, -1), (-1, -1), (-1, 1)
        )
        if promotion:
            self.updateSquares()

    def updateSquares(self, init=False):
        super().linearUpdateSquares(init)