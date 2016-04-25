from PyQt4 import QtCore
#from PyQt5 import QtCore


class Repo(QtCore.QObject):
    commit_processed = QtCore.pyqtSignal()
    issue_processed = QtCore.pyqtSignal()
    def __init__(self, _name, _gh=None):
        QtCore.QObject.__init__(self)
        self.name = _name
        if _gh is None:
            self.read_cache()  # If no github object is passed in, look in cache
        else:
            self.repo = _gh.get_repo(self.name)
            #self.commits = [self.pull_commits(repo)
            self.commits = []
            self.issues = []
            self.commit_page = 0
            self.issue_page = 0

            self.commit_timer = QtCore.QTimer()
            self.commit_timer.setInterval(1000)
            self.commit_timer.timeout.connect(self.pull_commits)
            self.commit_timer.start()

            self.issue_timer = QtCore.QTimer()
            self.issue_timer.setInterval(200)
            self.issue_timer.timeout.connect(self.pull_issues)
            self.issue_timer.start()
            #self.pull_commits(repo)
            #self.pull_issues(repo)

    def pull_commits(self):
        commits_list = self.repo.get_commits()
        page = commits_list.get_page(self.commit_page)
        if len(page) == 0:
            self.commit_timer.stop()
            return
        else:
            self.commits += [Commit(commit) for commit in page]
            self.commit_processed.emit()
            self.commit_page += 1

    def pull_issues(self):
        print("ISSUE TIMER TIMEOUT")
        issues_list = self.repo.get_issues(state='all')
        page = issues_list.get_page(self.issue_page)
        if len(page) == 0:
            self.issue_timer.stop()
            return
        else:
            self.issues += [Issue(issue) for issue in page]
            self.issue_processed.emit()
            self.issue_page += 1

    def read_cache(self):
        pass  # TODO: Implement cache

    def save_cache(self):
        pass  # TODO: Implement cache


class Issue(QtCore.QObject):
    def __init__(self, issue):
        self.created_at = issue.created_at
        self.closed_at = issue.closed_at
        self.title = issue.title
        self.labels = [label.name for label in issue.labels]


class Commit(QtCore.QObject):
    def __init__(self, commit):
        self.committer = commit.commit.committer.name
        self.message = commit.commit.message
        self.last_modified = commit.last_modified
