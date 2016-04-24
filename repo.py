from PyQt4 import QtCore
#from PyQt5 import QtCore


class Repo(QtCore.QObject):
    def __init__(self, _name, _gh=None):
        self.name = _name
        self.commit_processed = QtCore.Signal()
        self.issue_processed = QtCore.Signal()
        if _gh is None:
            self.read_cache()  # If no github object is passed in, look in cache
        else:
            repo = _gh.get_repo(self.name)
            #self.commits = [self.pull_commits(repo)
            self.commits = []
            self.issues = []

            self.pull_commits(repo)
            self.pull_issues(repo)

    def pull_commits(self, repo):
        commits_list = repo.get_commits()
        page_count = 0
        page = commits_list.get_page(page_count)
        while len(page) > 0:
            self.commits += [Commit(commit) for commit in page]
            page_count += 1
            page = commits_list.get_page(page_count)
            self.commit_processed.emit()

    def pull_issues(self, repo):
        issues_list = repo.get_issues(state='all')
        page_count = 0
        page = issues_list.get_page(page_count)
        while len(page) > 0:
            self.issues += [Issue(issue) for issue in page]
            page_count += 1
            page = issues_list.get_page(page_count)
            self.issue_processed.commit()

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
