import sys
# import csv
# import random
# import json
from datetime import datetime

from github import Github
from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from scipy import interpolate

from repo import Repo, toUnix, sortByKey
from github.GithubObject import NotSet


class TimeAxisItem(pg.AxisItem):

    def __ini__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%b %d, %Y") for value in values]

yearseconds = (datetime(3, 1, 1) - datetime(1, 1, 1)).total_seconds()


class Plot(pg.PlotItem):

    def __init__(self, numCurves=0, data=None, **kargs):
        super(Plot, self).__init__(**kargs)

        today = toUnix(datetime.today())

        self.data = data

        self.disableAutoRange(axis=self.getViewBox().XAxis)
        self.setXRange(today - yearseconds, today)
        self.auto = False

        self.curves = [self.plot() for i in range(numCurves)]
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen='k')
        self.addItem(self.vline)

        self.legend = self.addLegend()

        self.linkedPlots = []

    def link(self, other):
        self.getViewBox().linkView(axis=self.getViewBox().XAxis,
                                   view=other.getViewBox())
        self.linkedPlots.append(other)
        other.linkedPlots.append(self)

    def changeData(self, data, titles):
        self.data = data
        for i, v in enumerate(titles):
            self.legend.addItem(self.curves[i],
                                titles[i])

    def updatePlot(self):
        plotdata = sortByKey(self.data)
        for i, curve in enumerate(self.curves):
            if i < len(plotdata) - 1:
                curve.setData(x=plotdata[0],
                              y=np.cumsum(plotdata[1 + i]),
                              pen=(i, len(self.curves)))
            else:
                curve.setData(x=plotdata[0],
                              y=np.cumsum([sum(plotdata[j][x] for j in range(1, len(plotdata)))
                                           for x in range(len(plotdata[0]))]),
                              pen=(i, len(self.curves)))

    def mouseMoved(self, event):
        if self.sceneBoundingRect().contains(event):
            point = self.getViewBox().mapSceneToView(event)
            self.vline.setPos(point.x())
            for link in self.linkedPlots:
                link.vline.setPos(point.x())


class Window(QtGui.QWidget):

    def __init__(self):
        super(Window, self).__init__()

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # Need to put in authentication
        self.github = Github()

        print(self.github.rate_limiting)
        self.createPlots()

        self.createUI()

    def createPlots(self):
        # today = toUnix(datetime.today())
        self.layout = pg.GraphicsLayoutWidget(self)

        self.issuesPlot = Plot(numCurves=1,
                               title="Open Issues",
                               labels={'left': "Number of Issues",
                                       'bottom': "Date"},
                               axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.layout.addItem(self.issuesPlot, row=0, col=0)
        self.issuesPlot.scene().sigMouseMoved.connect(self.issuesPlot.mouseMoved)

        self.commitsPlot = Plot(numCurves=2,
                                title="Bugfix Commits (Red) vs Feature Commits (Blue)",
                                labels={'left': "Number of Commits",
                                        'bottom': "Date"},
                                axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.layout.addItem(self.commitsPlot, row=1, col=0)
        self.commitsPlot.scene().sigMouseMoved.connect(self.commitsPlot.mouseMoved)
        self.commitsPlot.link(self.issuesPlot)

        self.linesPlot = Plot(numCurves=3,
                              title="Number of Lines Added and Removed",
                              labels={'left': "Number of Lines",
                                      'bottom': "Date"},
                              axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.layout.addItem(self.linesPlot, row=2, col=0)
        self.linesPlot.scene().sigMouseMoved.connect(self.linesPlot.mouseMoved)
        self.linesPlot.link(self.issuesPlot)
        self.linesPlot.link(self.commitsPlot)

    def createUI(self):
        self.repoEdit = QtGui.QLineEdit(self)
        self.repoStart = QtGui.QPushButton("Start", self)
        self.repoStart.clicked.connect(self.createRepo)
        self.repoStop = QtGui.QPushButton("Stop", self)
        self.repoStop.clicked.connect(self.stopRepo)

        self.repoLabel = QtGui.QLabel(self)
        self.repoLabel.setText("Enter Repository:")

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.repoEdit)
        hbox.addWidget(self.repoStart)
        hbox.addWidget(self.repoStop)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.repoLabel)
        vbox.addLayout(hbox)
        vbox.addWidget(self.layout)

        self.setLayout(vbox)

        self.setGeometry(400, 400, 1000, 1000)
        self.setWindowTitle("GithubVis")

    def createRepo(self):
        print("Getting repo: ", self.repoEdit.text())
        #testDateSince1 = datetime(2016, 3, 18)
        #testDateSince1 = datetime(2012, 5, 7)
        #testDateUntil1 = datetime(2016, 3, 25)
        testDateSince1 = NotSet
        testDateUntil1 = NotSet
        self.repo = Repo(self.repoEdit.text(), _since=testDateSince1,
                         _until=testDateUntil1, _gh=self.github)

        self.issuesPlot.changeData(self.repo.issuesData, ["Open Issues"])
        self.commitsPlot.changeData(self.repo.commitsData[0:3],
                                    ["Bugfixes", "Features"])
        self.linesPlot.changeData([self.repo.commitsData[0],
                                   self.repo.commitsData[3],
                                   self.repo.commitsData[4]],
                                  ["Additions", "Removals", "Total"])
        self.repo.issueProcessed.connect(self.issuesPlot.updatePlot)
        self.repo.commitProcessed.connect(self.commitsPlot.updatePlot)
        self.repo.commitProcessed.connect(self.linesPlot.updatePlot)

    def stopRepo(self):
        self.repo.issueTimer.stop()
        self.repo.commitTimer.stop()
        self.repo.milestoneTimer.stop()

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
