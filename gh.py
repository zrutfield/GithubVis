import sys
from github import Github
from matplotlib import pyplot as plt
from matplotlib import dates
import datetime


if __name__ == "__main__":
    if (len(sys.argv) != 2):
        print "Usage: python " + sys.argv[0] + " user/repo"
        sys.exit()
    repo_name = sys.argv[1]

    user = ""
    password = ""

    g = Github(user, password)

    repo = g.get_repo(repo_name)

    issue_x = []
    issue_y = []
    counter = 0
    for issue in repo.get_issues():
        curr_issue_date = dates.date2num([issue.created_at, datetime.datetime.today()])
        curr_issue_values = [counter, counter]
        counter += 1
        issue_x.append(curr_issue_date)
        issue_y.append(curr_issue_values)

    for x, y in zip(issue_x, issue_y):
        plt.plot_date(x, y, 'r-')

    plt.show()
