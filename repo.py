import re
from datetime import datetime
from bisect import bisect_left

from github import Github, GithubException
from github.GithubObject import NotSet
from PyQt4 import QtCore
#from PyQt5 import QtCore


bugsearch = re.compile(
    "(fix)|(bug)|(issue)|(mistake)|(incorrect)|(fault)|(defect)|(error)|(flaw)", re.IGNORECASE)


unixDt = datetime(1970, 1, 1)


def toUnix(time):
    return (time - unixDt).total_seconds()

# Sorts a list of lists by the first list in the set


def sortByKey(data):
    return [list(x) for x in zip(*sorted(zip(*data), key=lambda p: p[0]))]


class Repo(QtCore.QObject):
    commitPulled = QtCore.pyqtSignal()
    issuePulled = QtCore.pyqtSignal()
    commitProcessed = QtCore.pyqtSignal()
    issueProcessed = QtCore.pyqtSignal()

    def __init__(self, _name, _since=NotSet, _until=NotSet, _gh=None):
        QtCore.QObject.__init__(self)
        self.name = _name

        self.since = _since
        self.until = _until

        self.commitsData = [[], [], [], [], []]
        self.issuesData = [[], []]

        if _gh is None:
            self.readCache()  # If no github object is passed in, look in cache
        else:
            self.repo = _gh.get_repo(self.name)
            self.unprocessedCommits = []
            self.unprocessedIssues = []
            self.unprocessedMilestones = []
            self.processedCommits = []
            self.processedIssues = []
            self.processedMilestones = []

            self.commitPage = 0
            self.issuePage = 0
            self.milestonePage = 0

            self.commitTimer = QtCore.QTimer()
            self.commitTimer.setInterval(200)
            self.commitTimer.timeout.connect(self.pullCommits)
            self.commitTimer.start()

            self.issueTimer = QtCore.QTimer()
            self.issueTimer.setInterval(200)
            self.issueTimer.timeout.connect(self.pullIssues)
            self.issueTimer.start()

            self.milestoneTimer = QtCore.QTimer()
            self.milestoneTimer.setInterval(200)
            self.milestoneTimer.timeout.connect(self.pullMilestones)
            self.milestoneTimer.start()

            self.commitPulled.connect(self.processCommits)
            self.issuePulled.connect(self.processIssues)

    def pullCommits(self):
        commitsList = self.repo.get_commits(since=self.since, until=self.until)
        #commitsList = self.repo.get_commits()
        try:
            page = commitsList.get_page(self.commitPage)
        except GithubException:
            print("Unknown Repository")
            self.commitTimer.stop()
            return

        if len(page) == 0:
            self.commitTimer.stop()
            return
        else:
            self.unprocessedCommits.append([Commit(commit) for commit in page])
            print("Pulled commit page")
            self.commitPulled.emit()
            self.commitPage += 1

    def processCommits(self):
        # Date, bugfix, feature, linesAdded, linesRemoved
        data = [[], [], [], [], []]
        while len(self.unprocessedCommits):
            block = self.unprocessedCommits.pop()
            for commit in block:
                date = toUnix(commit.commitDate)
                isBug = self.classifyCommitMessage(commit.message)
                data[0].append(date)
                if isBug:
                    data[1].append(1)
                    data[2].append(0)
                else:
                    data[1].append(0)
                    data[2].append(1)

                data[3].append(commit.linesAdded)
                data[4].append(commit.linesRemoved)
                self.processedCommits.append(commit)
        for i in range(len(data)):
            self.commitsData[i][0:0] = data[i]
        self.commitsData = sortByKey(self.commitsData)
        print("Processed", len(data[0]), "commits")
        self.commitProcessed.emit()

    def classifyCommitMessage(self, message):
        return bugsearch.search(message) != None

    def pullIssues(self):
        #issuesList = self.repo.get_issues(state='all', since=self.since)
        issuesList = self.repo.get_issues(state='all')
        try:
            page = issuesList.get_page(self.issuePage)
        except GithubException:
            print("Unknown Repository")
            self.issueTimer.stop()
            return

        if len(page) == 0:
            self.issueTimer.stop()
            return
        else:
            processedPage = [Issue(issue) for issue in filter(lambda x: (
                self.since is NotSet or x.created_at >= self.since), page)]
            #processedPage = [Issue(issue) for issue in filter(lambda x: (self.until is NotSet or x.created_at <= self.until) and (self.since is NotSet or x.created_at >= self.since), page)]
            # if len(processedPage) == 0:
            #    self.issuePage += 1
            #    return
            #processedPage = [Issue(issue) for issue in page]
            self.unprocessedIssues.append(processedPage)
            #self.unprocessedIssues.append([Issue(issue) for issue in page])
            self.issuePulled.emit()
            self.issuePage += 1

    def processIssues(self):
        data = [[], []]
        while len(self.unprocessedIssues):
            block = self.unprocessedIssues.pop()
            for issue in block:
                date = toUnix(issue.createdAt)
                data[0].append(date)
                data[1].append(1)
                if issue.closedAt is not None:
                    close = toUnix(issue.closedAt)
                    data[0].append(close)
                    data[1].append(-1)
                self.processedIssues.append(issue)
        self.issuesData[0][0:0] = data[0]
        self.issuesData[1][0:0] = data[1]
        self.issuesData = sortByKey(self.issuesData)
        print("Processed", len(data[0]), "issues")
        self.issueProcessed.emit()

    def pullMilestones(self):
        milestonesList = self.repo.get_milestones(state='all')
        try:
            page = milestonesList.get_page(self.milestonePage)
        except GithubException:
            print("Unknown Repository")
            self.milestoneTimer.stop()
            return

        if len(page) == 0:
            self.milestoneTimer.stop()
            return
        else:
            self.unprocessedMilestones.append(
                [Milestone(milestone) for milestone in page])
            # self.milestonePulled.emit()
            self.milestonePage += 1

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
        #self.linesAdded = commit.stats.additions
        #self.linesRemoved = commit.stats.deletions

    def __str__(self):
        return "".join(["Commit(", str(self.committer), ", ", str(self.message), ", ",
                        str(self.commitDate), ", ", str(self.lastModified), ")"])


class Milestone(QtCore.QObject):

    def __init__(self, milestone):
        self.title = milestone.title
        self.createdAt = milestone.created_at
        self.dueOn = milestone.due_on
        self.closedIssues = milestone.closed_issues
        self.openIssues = milestone.open_issues
        self.state = milestone.state
        self.updatedAt = milestone.updated_at

    def __str__(self):
        return "".join(["Milestone(", str(self.title), ", ", str(self.createdAt), ", ",
                        str(self.dueOn), ", ", str(self.closedIssues), ", ",
                        str(self.openIssues), ", ", str(self.state), ")"])
