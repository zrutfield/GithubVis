import sys
import csv
import random
import json
from datetime import datetime

from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from scipy import interpolate

class Window(QtGui.QWidget):
    def __init__(self):
        super(Window, self).__init__()

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.createPlots()
        
        self.createUI()

    def createPlots(self):
        self.layout = pg.GraphicsLayoutWidget(self)
        self.issuesPlot = self.layout.addPlot(row=0, col=0)
        self.issuesCurve = self.issuesPlot.plot()
        self.commitsPlot = self.layout.addPlot(row=1, col=0)
        

    def createUI(self):
        self.repoEdit = QtGui.QLineEdit(self)
        self.repoStart = QtGui.QPushButton("Start", self)
        self.repoStart.clicked.connect(self.createRepo)
        
        self.repoLabel = QtGui.QLabel(self)
        self.repoLabel.setText("Enter Repository:")

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.repoEdit)
        hbox.addWidget(self.repoStart)
        
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.repoLabel)
        vbox.addLayout(hbox)
        vbox.addWidget(self.layout)

        self.setLayout(vbox)

        self.setGeometry(400, 400, 1000, 1000)
        self.setWindowTitle("GithubVis")

    def createRepo(self):
        self.repo = Repo(self.repoEdit.getText())


    def processIssuesData(self):
        dates = {}
        issues = self.repo.issues
        for issue in issues:
            create = issue.created_at
            if create in dates:
                dates[create] += 1
            else:
                dates[create] = 1

            close = issue.closed_at
            if close is not None:
                if close in dates:
                    dates[close] -= 1
                else:
                    dates[close] = -1
        dates = list(dates)
        print(dates)
        sorted(dates, key=lambda d: d[0])
        total = 0
        for date in dates:
            total += date[1]
            date[1] = total
        self.issuesData = []
        self.issuesData[0] = [d[0] for d in dates]
        self.issuesData[1] = [d[1] for d in dates]

    def updateIssuesPlot(self):
        sl = smoothLine(self.issuesData[0], self.issuesData[1])
        self.issuesCurve.setData(x=sl[0], y=sl[1])

    def smoothLine(self, x, y):
        spline = interpolate.UnivariateSpline(x, y)
        x1 = np.linspace(min(x), max(x), num=len(x)*10)
        y1 = splint(x1)
        return (x1, y1)
    

def main():
    app = QtGui.QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())
    
    
if __name__ == "__main__":
    main()
