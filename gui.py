import sys
import csv
import random
import json
import re
from datetime import datetime

from github import Github
from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from scipy import interpolate

from repo import Repo, Issue, Commit

bugsearch = re.compile(
    "(fix)|(bug)|(issue)|(mistake)|(incorrect)|(fault)|(defect)|(error)|(flaw)", re.IGNORECASE)

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
        self.processIssuesData()
        print("Process")
        self.updateIssuesPlot()
        print("Plotted")
        self.processCommitsData()
        print("Process")
        self.updateCommitsPlot()
        print("Plotted")

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
        total = 0
        unixDT = datetime(1970, 1, 1)
        self.issuesData = [[], []]
        for date in dates.items():
            self.issuesData[0].append((date[0] - unixDT).total_seconds())
            self.issuesData[1].append(date[1])
        self.issuesData = self.sortByKey(self.issuesData)
        for i in range(1, len(self.issuesData[1])):
            self.issuesData[1][i] += self.issuesData[1][i-1]

    def updateIssuesPlot(self):
        #print(self.issuesData)
        sl = self.smoothLine(self.issuesData[0], self.issuesData[1])
        self.issuesCurve.setData(x=self.issuesData[0], y=self.issuesData[1], pen='r')
        #self.issuesCurve.setData(x=sl[0], y=sl[1], pen='r')

    def processCommitsData(self):
        unixDt = datetime(1970, 1, 1)
        self.commitsData = [[], [], []]
        commits = self.repo.commits
        for commit in commits:
            date = (commit.commit_date - unixDt).total_seconds()
            isBug = self.classifyCommitMessage(commit.message)
            self.commitsData[0].append(date)
            if isBug:
                self.commitsData[1].append(1)
                self.commitsData[2].append(0)
            else:
                self.commitsData[1].append(0)
                self.commitsData[2].append(1)
        self.commitsData = self.sortByKey(self.commitsData)
        for i in range(1, len(self.commitsData[0])):
            self.commitsData[1][i] += self.commitsData[1][i-1]
            self.commitsData[2][i] += self.commitsData[2][i-1]

        #print(self.commitsData[0])
        #print(self.densify(self.commitsData[0], 10))

    def classifyCommitMessage(self, message):
        return bugsearch.search(message) != None

    def updateCommitsPlot(self):
        size = len(self.commitsData[0])
        #y0 = np.zeros(size)
        #self.commitsPlot.plot(x=self.commitsData[0], y=y0)
        #y0 = [y0[i] + self.commitsData[1][i] for i in range(size)]
        y0 = self.commitsData[1][:]
        self.commitsBugsCurve.setData(x=self.commitsData[0], y=y0, pen='r')
        #sy = self.smoothLine(self.commitsData[0], y0)
        #self.commitsBugsCurve.setData(x=sy[0], y=sy[1], pen='r')
        y0 = [y0[i] + self.commitsData[2][i] for i in range(size)]
        self.commitsFeaturesCurve.setData(x=self.commitsData[0], y=y0, pen='b')
        #sy = self.smoothLine(self.commitsData[0], y0)
        #self.commitsFeaturesCurve.setData(x=sy[0], y=sy[1], pen='b')

    def smoothLine(self, x, y):
        spline = interpolate.UnivariateSpline(x, y)
        #x1 = np.linspace(min(x), max(x), num=len(x)*100)
        x1 = self.densify(x, 10)
        y1 = spline(x1)
        return (x1, y1)

    def densify(self, x, d):
        dx = []
        for i in range(1, len(x)):
            x0 = x[i-1]
            x1 = x[i]
            for n in range(d):
                dx.append(x0 + (n*(x1 - x0)/d))
        return dx
            

    # Sorts a list of lists by the first list in the set
    def sortByKey(self, data):
        return [list(x) for x in zip(*sorted(zip(*data), key=lambda p: p[0]))]
    

def main():
    app = QtGui.QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())
    
    
if __name__ == "__main__":
    main()
