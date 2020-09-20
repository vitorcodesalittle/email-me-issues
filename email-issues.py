import requests
import json
import io
import urllib.parse
import datetime
import re
import sched
import time
from bs4 import BeautifulSoup
from datetime import datetime

# https://docs.python.org/3/library/sched.html
s = sched.scheduler(time.time, time.sleep)

issue_id_regex = re.compile('#[0-9]+')

# Web crawling needed selectors
selectors = {
  # A span inside the issue div containing "#<id> opened on <date> by <username>"
  'id-span': 'span[class="opened-by"]',
  # The div of the issue. Select by appending issue id like: issue_9999,
  'issue-div': lambda id : 'issue_{}'.format(id),
  # Issue title: 
  'issue-title': lambda id : 'a[id="issue_{}_link"'.format(id)
}

last_time_checked = datetime(1900, 1, 1)
# Gets the complete url
def build_issues_url(url, tag):
  if tag:
    return url + "/labels/" + urllib.parse.quote(tag)
  else:
    return url + "/issues"

def get_issues_html(url):
  return requests.get(url).content

def extract(str, regex):
  m = re.search(regex, str)
  if m:
    s = m.span()
    return str[s[0]:s[1]]
  else:
    return None

def get_recent_issues(issues_html, from_data):
  soup = BeautifulSoup(issues_html, 'html.parser')
  opened_by_tags = soup.select(selectors['id-span'])
  new_issues = []
  for tag in opened_by_tags:
    issue_id = extract(str(tag), issue_id_regex)
    relative_time_tag = next((x for x in tag.contents if x.name == 'relative-time'), None)
    datetime_raw = relative_time_tag['datetime']
    date = datetime.strptime(datetime_raw, '%Y-%m-%dT%H:%M:%SZ')
    if date > last_time_checked:
      new_issues.append(issue_id)
  return new_issues

config_path = './config.json'
config_raw = io.open(config_path, mode="r")
config= json.loads(config_raw.read())
repos = config['repos']
timeout = config['interval']

for repo in repos:
  link = repo['link']
  tags = repo['issue_tags']
  repo['urls'] = [ build_issues_url(link, t) for t in tags ]

def run():
  global last_time_checked
  for repo in repos:
    for url in repo['urls']:
      html = get_issues_html(url)
      issues = get_recent_issues(html, datetime.now())
      print("NEW ISSUES OF {}: ".format(repo), issues)
  last_time_checked = datetime.now()
  s.enter(timeout, 1, run)

s.enter(timeout, 1, run)

s.run(True)

