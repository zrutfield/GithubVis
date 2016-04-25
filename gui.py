import sys
#import csv
#import random
#import json
from datetime import datetime

from github import Github
from PyQt4 import QtGui  # , QtCore
import pyqtgraph as pg
import numpy as np
from scipy import interpolate

from repo import Repo

class TimeAxisItem(pg.AxisItem):
    def __ini__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%b %d, %Y") for value in values]
        

class Window(QtGui.QWidget):
    def __init__(self):
        super(Window, self).__init__()

        #pg.setConfigOption('background', 'w')
        #pg.setConfigOption('foreground', 'k')

        self.github = Github()  # Need to put in authentication

        print(self.github.rate_limiting)
        self.createPlots()

        self.createUI()

    def createPlots(self):
        self.layout = pg.GraphicsLayoutWidget(self)
        self.issuesPlot = self.layout.addPlot(row=0, col=0, title="Issues",
                                              axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.issuesCurve = self.issuesPlot.plot()
        self.commitsPlot = self.layout.addPlot(row=1, col=0, title="Commits",
                                              axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.commitsBugsCurve = self.commitsPlot.plot()
        self.commitsFeaturesCurve = self.commitsPlot.plot()

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
        print("Getting repo: ", self.repoEdit.text())
        self.repo = Repo(self.repoEdit.text(), self.github)
        print("Got data")
        self.repo.issueProcessed.connect(self.updateIssuesPlot)
        self.repo.commitProcessed.connect(self.updateCommitPlot)


    def updateIssuesPlot(self):
        #sl = self.smoothLine(self.issuesData[0], self.issuesData[1])
        #self.issuesCurve.clear()
        self.issuesCurve.setData(x=self.repo.issuesData[0], y=self.repo.issuesData[1], pen='r')
        #self.issuesCurve.setData(x=sl[0], y=sl[1], pen='r')

    def updateCommitPlot(self):
        size = len(self.repo.commitsData[0])
        #y0 = np.zeros(size)
        #self.commitsPlot.plot(x=self.commitsData[0], y=y0)
        #y0 = [y0[i] + self.commitsData[1][i] for i in range(size)]
        y0 = self.repo.commitsData[1][:]
        self.commitsBugsCurve.setData(x=self.repo.commitsData[0], y=y0, pen='r')
        #sy = self.smoothLine(self.commitsData[0], y0)
        #self.commitsBugsCurve.setData(x=sy[0], y=sy[1], pen='r')
        y0 = [y0[i] + self.repo.commitsData[2][i] for i in range(size)]
        self.commitsFeaturesCurve.setData(x=self.repo.commitsData[0], y=y0, pen='b')
        #sy = self.smoothLine(self.commitsData[0], y0)
        #self.commitsFeaturesCurve.setData(x=sy[0], y=sy[1], pen='b')

    def smoothLine(self, x, y):
        spline = interpolate.UnivariateSpline(x, y)
        x1 = np.linspace(min(x), max(x), num=len(x) * 100)
        y1 = spline(x1)
        return (x1, y1)


def main():
    app = QtGui.QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
