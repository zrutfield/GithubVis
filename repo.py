import re
from datetime import datetime

from PyQt4 import QtCore
#from PyQt5 import QtCore


bugsearch = re.compile(
    "(fix)|(bug)|(issue)|(mistake)|(incorrect)|(fault)|(defect)|(error)|(flaw)", re.IGNORECASE)


# Sorts a list of lists by the first list in the set
def sortByKey(data):
    return [list(x) for x in zip(*sorted(zip(*data), key=lambda p: p[0]))]

class Repo(QtCore.QObject):
    commitPulled = QtCore.pyqtSignal()
    issuePulled = QtCore.pyqtSignal()
    commitProcessed = QtCore.pyqtSignal()
    issueProcessed = QtCore.pyqtSignal()
    
    def __init__(self, _name, _gh=None):
        QtCore.QObject.__init__(self)
        self.name = _name
        
        self.unixDt = datetime(1970, 1, 1)
        self.commitsData = [[], [], []]
        self.issuesData = [[], []]
        
        if _gh is None:
            self.readCache()  # If no github object is passed in, look in cache
        else:
            self.repo = _gh.get_repo(self.name)
            #self.commits = [self.pull_commits(repo)
            self.unprocessedCommits = []
            self.unprocessedIssues = []
            self.processedCommits = []
            self.processedIssues = []
            
            self.commitPage = 0
            self.issuePage = 0

            self.commitTimer = QtCore.QTimer()
            self.commitTimer.setInterval(200)
            self.commitTimer.timeout.connect(self.pullCommits)
            self.commitTimer.start()

            self.issueTimer = QtCore.QTimer()
            self.issueTimer.setInterval(200)
            self.issueTimer.timeout.connect(self.pullIssues)
            self.issueTimer.start()

            self.commitPulled.connect(self.processCommits)
            self.issuePulled.connect(self.processIssues)

    def pullCommits(self):
        commitsList = self.repo.get_commits()
        page = commitsList.get_page(self.commitPage)
        if len(page) == 0:
            self.commitTimer.stop()
            return
        else:
            self.unprocessedCommits.append([Commit(commit) for commit in page])
            self.commitPulled.emit()
            self.commitPage += 1

    def processCommits(self):
        data = [[], [], []]
        while len(self.unprocessedCommits):
            block = self.unprocessedCommits.pop()
            for commit in block:
                date = self.toUnix(commit.commitDate)
                isBug = self.classifyCommitMessage(commit.message)
                data[0].append(date)
                if isBug:
                    data[1].append(1)
                    data[2].append(0)
                else:
                    data[1].append(0)
                    data[2].append(1)
                self.processedCommits.append(commit)
        data = sortByKey(data)
        for i in range(1, len(data[0])):
            data[1][i] += data[1][i-1]
            data[2][i] += data[2][i-1]
        total = [0, 0]
        total[0] = data[1][-1]
        total[1] = data[2][-1]
        for i in range(0, len(self.commitsData[0])):
            self.commitsData[1][i] += total[0]
            self.commitsData[2][i] += total[1]
        self.commitsData[0][0:0] = data[0]
        self.commitsData[1][0:0] = data[1]
        self.commitsData[2][0:0] = data[2]
        self.commitProcessed.emit()

    def classifyCommitMessage(self, message):
        return bugsearch.search(message) != None

    def pullIssues(self):
        issuesList = self.repo.get_issues(state='all')
        page = issuesList.get_page(self.issuePage)
        if len(page) == 0:
            self.issueTimer.stop()
            return
        else:
            self.unprocessedIssues.append([Issue(issue) for issue in page])
            self.issuePulled.emit()
            self.issuePage += 1

    def processIssues(self):
        data = [[], []]
        while len(self.unprocessedIssues):
            block = self.unprocessedIssues.pop()
            for issue in block:
                date = self.toUnix(issue.createdAt)
                data[0].append(date)
                data[1].append(1)
                if issue.closedAt is not None:
                    close = self.toUnix(issue.closedAt)
                    data[0].append(close)
                    data[1].append(-1)
                    self.processedIssues.append(issue)
        data = sortByKey(data)
        for i in range(1, len(data[0])):
            data[1][i] += data[1][i-1]
        total = data[1][-1]
        for i in range(0, len(self.issuesData[0])):
            self.issuesData[1][i] += total
        self.issuesData[0][0:0] = data[0]
        self.issuesData[1][0:0] = data[1]
        self.issueProcessed.emit()

    def toUnix(self, time):
        return (time - self.unixDt).total_seconds()

    def read_cache(self):
        pass  # TODO: Implement cache

    def save_cache(self):
        pass  # TODO: Implement cache


class Issue(QtCore.QObject):
    def __init__(self, issue):
        self.createdAt = issue.created_at
        self.closedAt = issue.closed_at
        self.title = issue.title
        self.labels = [label.name for label in issue.labels]

    def __str__(self):
        return "".join(["Issue(", str(self.createdAt), ", ", str(self.closedAt), ", ",
                        str(self.title), ")"])


class Commit(QtCore.QObject):
    def __init__(self, commit):
        self.committer = commit.commit.committer.name
        self.message = commit.commit.message
        self.commitDate = commit.commit.committer.date
        self.lastModified = commit.last_modified

    def __str__(self):
        return "".join(["Commit(", str(self.committer), ", ", str(self.message), ", ",
                        str(self.commitDate), ", ", str(self.lastModified), ")"])
