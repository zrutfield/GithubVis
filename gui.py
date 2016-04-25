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


class Window(QtGui.QWidget):
    def __init__(self):
        super(Window, self).__init__()

        #pg.setConfigOption('background', 'w')
        #pg.setConfigOption('foreground', 'k')

        #print(self.github.rate_limiting)
        self.github = Github( )  # Need to put in authentication

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
        print("Getting repo: ", self.repoEdit.text())
        self.repo = Repo(self.repoEdit.text(), self.github)
        print("Got data")
        self.repo.issue_processed.connect(self.processIssuesData)
        #self.processIssuesData()
        #print("Process")
        #self.updateIssuesPlot()
        print("Plotted")

    def processIssuesData(self):
        dates = {}
        issues = self.repo.issues
        if len(issues) == 0:
            return
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
        #total = 0
        unixDT = datetime(1970, 1, 1)
        self.issuesData = [[], []]
        for date in dates.items():
            self.issuesData[0].append((date[0] - unixDT).total_seconds())
            self.issuesData[1].append(date[1])
        self.issuesData = [list(x) for x in zip(*sorted(zip(self.issuesData[0], self.issuesData[1]), key=lambda p: p[0]))]
        for i in range(1, len(self.issuesData[1])):
            self.issuesData[1][i] += self.issuesData[1][i - 1]
        print("Process")
        self.updateIssuesPlot()
        print("Plotted")

    def updateIssuesPlot(self):
        #sl = self.smoothLine(self.issuesData[0], self.issuesData[1])
        self.issuesCurve.clear()
        self.issuesCurve.setData(x=self.issuesData[0], y=self.issuesData[1], pen='r')
        #self.issuesCurve.setData(x=sl[0], y=sl[1], pen='r')

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
