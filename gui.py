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
from bisect import bisect_left

from repo import Repo, toUnix, sortByKey, unixDt
from github.GithubObject import NotSet

# Axis for plotting dates, used by the plots
class TimeAxisItem(pg.AxisItem):

    def __ini__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%b %d, %Y") for value in values]

# Years time converted to seconds
yearseconds = (datetime(1, 7, 1) - datetime(1, 1, 1)).total_seconds()

# Plot object
class Plot(pg.PlotItem):

    def __init__(self, numCurves=0, data=[[]], **kargs):
        super(Plot, self).__init__(**kargs)

        today = toUnix(datetime.today())

        self.data = data
        self.plotdata = data

        # Disable auto range until data time is greater than a year
        self.disableAutoRange(axis=self.getViewBox().XAxis)
        self.setXRange(today - yearseconds, today)
        self.auto = False
        self.doAuto = True

        self.setLimits(yMin=0,
                       xMax=today)
        self.sigRangeChanged.connect(self.rangeChange)

        self.curves = [self.plot() for i in range(numCurves)]
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen='k')
        self.addItem(self.vline)

        # Add legend
        self.legend = self.addLegend()
        self.legend.anchor(0, 0)
        self.titles = []

        self.htmltext = ''.join(['<div style="text-align: center"><span style="color: #FFF;">',
                                 '</span></div>'])
        self.text = pg.TextItem(html=self.htmltext,
                                anchor=(1.0, 0), border='w', fill=(0, 0, 0, 100))
        self.text.setPos(self.vline.pos())
        self.showText = False

        self.linkedPlots = []

        self.milestoneData = [[], []]
        self.milestoneVbars = []
        self.milestoneTexts = []

    # Link this plot to another, ensuring scales are adjusted on both
    def link(self, other):
        self.getViewBox().linkView(axis=self.getViewBox().XAxis,
                                   view=other.getViewBox())
        self.linkedPlots.append(other)
        other.linkedPlots.append(self)

    # Clear plot for changing datasets
    def clear(self):
        self.data = [[]]
        self.plotdata = self.data
        for t in self.titles:
            self.legend.removeItem(t)

        for v in self.milestoneVbars:
            self.removeItem(v)
        for t in self.milestoneTexts:
            self.removeItem(t)
        for c in self.curves:
            c.setData(x=[], y=[])

        today = toUnix(datetime.today())
        self.setXRange(today - yearseconds, today)
        self.auto = False
        self.doAuto = True

    # Change datasets
    def changeData(self, data, titles):
        self.clear()

        self.data = data
        self.titles = titles
        # Add curve for each set of data in plot
        for i, v in enumerate(titles):
            self.legend.addItem(self.curves[i],
                                titles[i])

    # Add a new milestone to be plotted on graph
    def addMilestone(self):
        for i in range(len(self.milestoneVbars), len(self.milestoneData[0])):
            vbar = pg.InfiniteLine(angle=90, movable=False, pen={'color': '#0F0',
                                                                 'width': 1})
            vbar.setValue(self.milestoneData[0][i])
            self.addItem(vbar)
            self.milestoneVbars.append(vbar)

            htmltext = ''.join(['<div style="text-align: center"><span style="color: #FFF;">',
                                self.milestoneData[1][i], '</span></div>'])
            text = pg.TextItem(html=htmltext,
                               anchor=(0, 1.0), border='w', fill=(0, 0, 0, 100))
            self.addItem(text)
            self.milestoneTexts.append(text)
            text.setPos(self.milestoneData[0][i], self.viewRange()[1][0])

    # Update plot with new data
    def updatePlot(self):
        self.plotdata = sortByKey(self.data)
        if self.doAuto and not self.auto and self.plotdata[0][-1] - self.plotdata[0][0] > yearseconds:
            # self.enableAutoRange(axis=self.getViewBox().XAxis)
            self.auto = True

        for i, curve in enumerate(self.curves):
            if i < len(self.plotdata) - 1:
                curve.setData(x=self.plotdata[0],
                              y=np.cumsum(self.plotdata[1 + i]),
                              pen={'color': (i, len(self.curves)),
                                   'width': 2})
            # If more curves than number of datasets, plot sum of datasets (used in additions/deletions plot)
            else:
                self.plotdata.append([sum(self.plotdata[j][x] for j in range(1, len(self.plotdata)))
                                      for x in range(len(self.plotdata[0]))])
                curve.setData(x=self.plotdata[0],
                              y=np.cumsum(self.plotdata[1 + i]),
                              pen={'color': (i, len(self.curves)),
                                   'width': 2})
        if self.doAuto and self.auto:
            self.autoRange()

    # Update mouse hover text
    def updateText(self):
        if len(self.data[0]) > 0:
            index = bisect_left(self.plotdata[0], self.vline.pos().x()) - 1
            if (index < 0 or index > len(self.data[0])):
                if self.showText:
                    self.removeItem(self.text)
                self.showText = False
                return
            if not self.showText:
                self.addItem(self.text)
                self.showText = True
            
            self.htmltext = ''.join(['<div style="text-align: center"><span style="color: #FFF;">',
                                     'Date = ', datetime.fromtimestamp(
                                         self.plotdata[0][index]).strftime("%b %d, %Y")])
            for i in range(len(self.curves)):
                self.htmltext = ''.join([self.htmltext, '<br>',
                                         self.titles[i], ' = ',
                                         str(sum(self.plotdata[i + 1][0:index]))])
            self.htmltext = ''.join([self.htmltext, '</span></div>'])
            self.text.setHtml(self.htmltext)
            self.text.setPos(self.vline.pos().x(), self.viewRange()[1][1])

    # Slot for catching mouse movement
    def mouseMoved(self, event):
        if self.sceneBoundingRect().contains(event):
            point = self.getViewBox().mapSceneToView(event)
            self.vline.setPos(point.x())
            for link in self.linkedPlots:
                link.vline.setPos(point.x())
        self.updateText()

    # Slot for catching a range change
    def rangeChange(self):
        for text in self.milestoneTexts:
            text.setPos(text.pos().x(), self.viewRange()[1][0])
        self.updateText()

    # Change range for date selection
    def setRange(self, start, end):
        if start is not None:
            self.setXRange(start, self.viewRange()[0][1])
        if end is not None:
            self.setXRange(self.viewRange()[0][0], end)


# Main window
class Window(QtGui.QWidget):

    def __init__(self):
        super(Window, self).__init__()

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # Need to put in authentication (token or user/pass)
        self.github = Github()

        print(self.github.rate_limiting)

        self.plots = []
        self.createPlots()

        self.createUI()

    def createPlots(self):
        # today = toUnix(datetime.today())
        self.layout = pg.GraphicsLayoutWidget(self)

        # Plot to show total number of open issues
        self.issuesPlot = Plot(numCurves=1,
                               title="Issues",
                               labels={'left': "Number of Issues",
                                       'bottom': "Date"},
                               axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.layout.addItem(self.issuesPlot, row=0, col=0)
        self.issuesPlot.scene().sigMouseMoved.connect(self.issuesPlot.mouseMoved)
        self.plots.append(self.issuesPlot)

        # Plot to show total commits, classified as bugfixes or features
        self.commitsPlot = Plot(numCurves=2,
                                title="Commits",
                                labels={'left': "Number of Commits",
                                        'bottom': "Date"},
                                axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.layout.addItem(self.commitsPlot, row=1, col=0)
        self.commitsPlot.scene().sigMouseMoved.connect(self.commitsPlot.mouseMoved)
        self.commitsPlot.link(self.issuesPlot)
        self.plots.append(self.commitsPlot)

        # Plot to show additions and deletions
        self.linesPlot = Plot(numCurves=3,
                              title="Lines of Code",
                              labels={'left': "Number of Lines",
                                      'bottom': "Date"},
                              axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.layout.addItem(self.linesPlot, row=2, col=0)
        self.linesPlot.scene().sigMouseMoved.connect(self.linesPlot.mouseMoved)
        self.linesPlot.link(self.issuesPlot)
        self.linesPlot.link(self.commitsPlot)
        self.plots.append(self.linesPlot)

    def createUI(self):
        # Line edit for entering repository
        self.repoEdit = QtGui.QLineEdit(self)
        self.repoStart = QtGui.QPushButton("Start", self)
        self.repoStart.clicked.connect(self.createRepo)
        self.repoStop = QtGui.QPushButton("Stop", self)
        self.repoStop.clicked.connect(self.stopRepo)

        self.repoLabel = QtGui.QLabel(self)
        self.repoLabel.setText("Enter Repository:")

        # Set date range
        self.startLabel = QtGui.QLabel(self)
        self.startLabel.setText("Start Date:")
        self.startDate = QtGui.QDateTimeEdit(self)
        self.startDate.setCalendarPopup(True)
        self.startDate.setDateTime(datetime.today())
        self.startDate.setDateTimeRange(unixDt, datetime.today())
        self.startDate.dateTimeChanged.connect(self.changeStartDate)

        self.endLabel = QtGui.QLabel(self)
        self.endLabel.setText("End Date:")
        self.endDate = QtGui.QDateTimeEdit(self)
        self.endDate.setCalendarPopup(True)
        self.endDate.setDateTime(datetime.today())
        self.endDate.setDateTimeRange(unixDt, datetime.today())
        self.endDate.dateTimeChanged.connect(self.changeEndDate)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.repoEdit)
        hbox.addWidget(self.repoStart)
        hbox.addWidget(self.repoStop)

        dhbox1 = QtGui.QHBoxLayout()
        dhbox1.addWidget(self.startLabel)
        dhbox1.addWidget(self.endLabel)

        dhbox2 = QtGui.QHBoxLayout()
        dhbox2.addWidget(self.startDate)
        dhbox2.addWidget(self.endDate)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.repoLabel)
        vbox.addLayout(hbox)
        vbox.addLayout(dhbox1)
        vbox.addLayout(dhbox2)
        vbox.addWidget(self.layout)

        self.setLayout(vbox)

        self.setGeometry(0, 0, 1024, 720)
        self.setWindowTitle("GithubVis")

    def createRepo(self):
        print("Getting repo: ", self.repoEdit.text())
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

        for p in self.plots:
            self.repo.milestoneProcessed.connect(p.addMilestone)
            p.milestoneData = self.repo.milestoneData

        self.startDate.setDateTime(self.repo.createdAt)

    def stopRepo(self):
        self.repo.stop()

    def smoothLine(self, x, y):
        spline = interpolate.UnivariateSpline(x, y)
        x1 = np.linspace(min(x), max(x), num=len(x) * 100)
        y1 = spline(x1)
        return (x1, y1)

    def changeStartDate(self, dt):
        for p in self.plots:
            p.doAuto = False
            p.setRange(toUnix(dt.toPyDateTime()), None)

    def changeEndDate(self, dt):
        for p in self.plots:
            p.doAuto = False
            p.setRange(None, toUnix(dt.toPyDateTime()))

def main():
    app = QtGui.QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
