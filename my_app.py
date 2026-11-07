from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout
from random import randint 
app = QApplication([])
main_win=QWidget()
main_win.setWindowTitle('Proyecto de diagnostico de salud')
but = QPushButton('Presione para empezar el rendimiento cardiaco')
text = QLabel('Rendimiento cardiaco')

winner = QLabel('Resultado del rendimiento cardiaco')
line = QVBoxLayout()
line.addWidget(text, alignment = Qt.AlignCenter)
line.addWidget(winner, alignment = Qt.AlignCenter)
line.addWidget(but, alignment = Qt.AlignCenter)
main_win.setLayout(line)
def show_winner():
    number = randint(0, 99)
    winner.setText(str(number))
    text.setText('')
but.clicked.connect(show_winner)
main_win.show()
app.exec_()