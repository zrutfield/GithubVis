import re
from datetime import datetime

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
    commitProcessed = QtCore.pyqtSignal()
    issueProcessed = QtCore.pyqtSignal()
    milestoneProcessed = QtCore.pyqtSignal()

    def __init__(self, _name, _since=NotSet, _until=NotSet, _gh=None):
        QtCore.QObject.__init__(self)
        self.name = _name

        self.since = _since
        self.until = _until

        self.commitsData = [[], [], [], [], []]
        self.issuesData = [[], []]
        self.milestoneData = [[], [], []]

        if _gh is None:
            self.readCache()  # If no github object is passed in, look in cache
        else:
            self.repo = _gh.get_repo(self.name)
            self.createdAt = self.repo.created_at

            self.processedCommits = []
            self.processedIssues = []
            self.processedMilestones = []

            # Create threads for pulling data
            self.commitThread = CommitThread(self.repo, self.since, self.until)
            self.commitThread.commitPulled.connect(self.processCommit)
            self.commitThread.start()

            self.issueThread = IssueThread(self.repo, self.since, self.until)
            self.issueThread.issuePulled.connect(self.processIssue)
            self.issueThread.start()

            self.milestoneThread = MilestoneThread(
                self.repo, self.since, self.until)
            self.milestoneThread.milestonePulled.connect(self.processMilestone)
            self.milestoneThread.start()

    def stop(self):
        self.commitThread.stop()
        self.issueThread.stop()
        self.milestoneThread.stop()

    # Process each new commit
    def processCommit(self, commit):
        commit = commit[0]
        self.commitsData[0].append(toUnix(commit.commitDate))
        isBug = self.classifyCommitMessage(commit.message)
        self.commitsData[1].append(int(isBug))
        self.commitsData[2].append(1 - int(isBug))
        self.commitsData[3].append(commit.linesAdded)
        self.commitsData[4].append(commit.linesRemoved)
        self.processedCommits.append(commit)
        self.commitProcessed.emit()

    # Classify a commit as bugfix or feature
    def classifyCommitMessage(self, message):
        return bugsearch.search(message) != None

    # Process each new issue
    def processIssue(self, issue):
        issue = issue[0]
        self.issuesData[0].append(toUnix(issue.createdAt))
        self.issuesData[1].append(1)
        if issue.closedAt is not None:
            self.issuesData[0].append(toUnix(issue.closedAt))
            self.issuesData[1].append(-1)
        self.issueProcessed.emit()

    # Process each new milestone
    def processMilestone(self, milestone):
        milestone = milestone[0]
        self.milestoneData[0].append(toUnix(milestone.createdAt))
        self.milestoneData[1].append(milestone.title)
        self.milestoneData[2].append('created')
        # if milestone.dueOn is not None:
        #     self.milestoneData[0].append(toUnix(milestone.dueOn))
        #     self.milestoneData[1].append(milestone.title)
        #     self.milestoneData[2].append('due')
        self.milestoneProcessed.emit()

    def read_cache(self):
        pass  # TODO: Implement cache

    def save_cache(self):
        pass  # TODO: Implement cache


# Thread object to pull commits
class CommitThread(QtCore.QThread):
    commitPulled = QtCore.pyqtSignal(list)

    def __init__(self, repo, since, until):
        super().__init__()
        self.repo = repo
        self.since = since
        self.until = until
        self.halt = False

    def run(self):
        commitsList = self.repo.get_commits(since=self.since, until=self.until)
        try:
            page = commitsList.get_page(0)
        except GithubException:
            print("Unknown Repository")
            return

        for commit in commitsList:
            if self.halt:
                return
            self.commitPulled.emit([Commit(commit)])

    def stop(self):
        self.halt = True


# Thread object to pull issues
class IssueThread(QtCore.QThread):
    issuePulled = QtCore.pyqtSignal(list)

    def __init__(self, repo, since, until):
        super().__init__()
        self.repo = repo
        self.since = since
        self.until = until
        self.halt = False

    def run(self):
        #issuesList = self.repo.get_issues(state='all', since=self.since)
        issuesList = self.repo.get_issues(state='all')
        try:
            page = issuesList.get_page(0)
        except GithubException:
            print("Unknown Repository")
            return

        for issue in issuesList:
            if self.halt:
                return
            if self.since is NotSet or issue.created_at >= self.since:
                self.issuePulled.emit([Issue(issue)])

    def stop(self):
        self.halt = True


# Thread object to pull milestones
class MilestoneThread(QtCore.QThread):
    milestonePulled = QtCore.pyqtSignal(list)

    def __init__(self, repo, since, until):
        super().__init__()
        self.repo = repo
        self.since = since
        self.until = until
        self.halt = False

    def run(self):
        milestonesList = self.repo.get_milestones(state='all')
        try:
            page = milestonesList.get_page(0)
        except GithubException:
            print("Unknown Repository")
            return

        for milestone in milestonesList:
            if self.halt:
                return
            self.milestonePulled.emit([Milestone(milestone)])

    def stop(self):
        self.halt = True


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
        self.linesAdded = commit.stats.additions
        self.linesRemoved = commit.stats.deletions

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
