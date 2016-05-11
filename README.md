# GithubVis
Visualizations of Github repositories

Shows graphs for the number of open issues, number of commits classified as either a bugfix or a feature, and number of lines of code added or removed.

Without authentication, only 60 requests to the Github API can be made per hour. With authentication, 5,000 requests can be made. To add authentication, put either a token or your user/pass into the Github object intialization field in the window (line 207 in gui.py).
