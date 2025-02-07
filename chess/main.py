import logging
import logging.config
import sys

import logger
from game import ChessGame
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget


LIGHT_SQUARE_COLOR: QColor = QColor(220, 220, 220)
DARK_SQUARE_COLOR: QColor = QColor(50, 50, 50)
LOGGING_LEVEL = logging.DEBUG


class MainWindow(QWidget):

    def __init__(
            self,
            light_square_color: QColor,
            dark_square_color: QColor
            ):
        super().__init__()
        self.setWindowTitle("Maxwell's Chess Game")
        self.showMaximized()

        # ChessGame reference
        self.currentGame = None

        self.light_square_color = light_square_color
        self.dark_square_color = dark_square_color
        # New game button
        newGameBtn = QPushButton("New Game")
        newGameBtn.clicked.connect(self.startNewGame)

        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(0,0,0,0)
        self.mainLayout.addWidget(newGameBtn)
        self.setLayout(self.mainLayout)
        
    def startNewGame(self):
        self.emptyWindow()
        self.currentGame = ChessGame(
            light_square_color=self.light_square_color,
            dark_square_color=self.dark_square_color
        )
        # Add game screen to window
        self.mainLayout.addWidget(self.currentGame)

    def emptyWindow(self):
        for i in reversed(range(self.mainLayout.count())):
            widget = self.mainLayout.itemAt(i).widget()
            self.mainLayout.removeWidget(widget)
            widget.hide()
            widget.destroy()


if __name__ == "__main__":
    logging.basicConfig(level=LOGGING_LEVEL, format="[5%(filename)s:%(lineno)s - %(funcName)s ()]: %(message)s")
    app = QApplication([])
    app.aboutToQuit.connect(logger.closeLog)

    main = MainWindow(
        light_square_color=LIGHT_SQUARE_COLOR,
        dark_square_color=DARK_SQUARE_COLOR
    )
    main.show()

    sys.exit(app.exec())