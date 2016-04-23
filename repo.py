class Repo:
    def __init__(self, _name, _gh=None):
        self.name = _name
        if _gh is None:
            self.read_cache()  # If no github object is passed in, look in cache
        else:
            repo = _gh.get_repo(self.name)
            #self.commits = [self.pull_commits(repo)
            self.commits = [Commit(commit) for commit in repo.get_commits()]
            self.issues = [Issue(issue) for issue in repo.get_issues(state='all')]

    def read_cache(self):
        pass  # TODO: Implement cache

    def save_cache(self):
        pass  # TODO: Implement cache


class Issue:
    def __init__(self, issue):
        self.created_at = issue.created_at
        self.closed_at = issue.closed_at
        self.title = issue.title
        self.labels = [label.name for label in issue.labels]


class Commit:
    def __init__(self, commit):
        self.committer = commit.commit.committer.name
        self.message = commit.commit.message
        self.last_modified = commit.last_modified
