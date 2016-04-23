import sys
from github import Github
from matplotlib import pyplot as plt
from matplotlib import dates
import datetime
import json
#import pygraphviz as pgv
import getpass


#def make_tree(json_dict):
#    tree = pgv.AGraph()
#    tree.add_node('head')
#    head = tree.get_node('head')
#    head.attr['label'] = "name: %s\nowner: %s" % (json_dict['name'], json_dict['owner'])
#    tree.add_edge('head', 'issues[]')
#    tree.add_edge('head', 'commits[]')

#    #counter = 1
#    #for issue in json_dict['issues']:
#    #    if counter > 3:
#    #        break
#    #    tree.add_edge('issues', issue)
#    #    counter += 1

#    tree.add_edge('issues[]', json_dict['issues'][0])
#    tree.add_edge('commits[]', json_dict['commits'][0])

#    tree.draw("tree.png", prog="dot")


def cache(gh, repo_name):
    print("Getting repo %s" % repo_name)
    repo = gh.get_repo(repo_name)
    owner, name = repo_name.split("/")
    fp = open("output.json", "w")

    repo_data = {"name" : name, "owner": owner}

    repo_data["issues"] = []
    repo_data["commits"] = []
    for issue in repo.get_issues():
        repo_data["issues"].append({"name": issue.title, "created_at": issue.created_at.isoformat()})

    for commit in repo.get_commits():
        repo_data["commits"].append({"committer": commit.commit.committer.name, "last_modified": commit.last_modified, "message": commit.commit.message})

    json.dump(repo_data, fp)
    #make_tree(repo_data)

    return repo_data

if __name__ == "__main__":
    if (len(sys.argv) != 2):
        print("Usage: python " + sys.argv[0] + " user/repo")
        sys.exit()
    repo_name = sys.argv[1]

    user = input("Username:")
    password = getpass.getpass("Password:")

    g = Github(user, password)

    cache(g, repo_name)

    repo = g.get_repo(repo_name)

    issue_x = []
    issue_y = []
    counter = 0
    min_date = dates.date2num(datetime.datetime.today())
    max_date = datetime.datetime.today()
    for issue in repo.get_issues(state='all'):
        closed_at = datetime.datetime.today() if issue.closed_at is None else issue.closed_at
        curr_issue_date = dates.date2num([issue.created_at, closed_at])
        min_date = min(min_date, dates.date2num(issue.created_at))
        curr_issue_values = [counter, counter]
        counter += 1
        issue_x.append(curr_issue_date)
        issue_y.append(curr_issue_values)

    for x, y in zip(issue_x, issue_y):
        plt.plot_date(x, y, 'r-')

    plt.axis([min_date, max_date, -0.2, len(issue_x) - 0.8])
    plt.title("Issues: " + repo_name)

    plt.show()
