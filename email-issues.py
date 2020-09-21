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
import smtplib
from email.message import EmailMessage
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

def build_single_issue_url(url, issue_id):
  return url + '/issues/' + issue_id[1:]

def get_issues_html(url):
  return requests.get(url).content

def extract(str, regex):
  m = re.search(regex, str)
  if m:
    s = m.span()
    return str[s[0]:s[1]]
  else:
    return None

def send_email(from_email, from_password, smtp_server,smtp_port, to_email, content, subject):
  me = from_email
  you = to_email
  s = smtplib.SMTP(smtp_server, port=smtp_port)
  s.ehlo()
  s.starttls()
  s.login(from_email, from_password)
  msg = EmailMessage()
  msg.set_content(content)

  # me == the sender's email address
  # you == the recipient's email address
  msg['Subject'] = subject
  msg['From'] = me
  msg['To'] = you
  # Send the message via SMTP server.
  try:
    s.send_message(msg)
    s.quit()
  except Exception as e:
    raise e

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



def run():
  config_path = './config.json'
  config_raw = io.open(config_path, mode="r")
  config= json.loads(config_raw.read())
  repos = config['repos']
  timeout = config['interval']
  from_email = config['sender-email']
  to_email = config['to-email']
  from_password = config['sender-password']
  server = config['smtp-server']
  port = config['server-port']
  subject = "New issues found!"

  for repo in repos:
    link = repo['link']
    tags = repo['issue_tags']
    repo['urls'] = [ build_issues_url(link, t) for t in tags ]
  global last_time_checked
  content = ''
  for repo in repos:
    for url in repo['urls']:
      html = get_issues_html(url)
      issues = get_recent_issues(html, last_time_checked)
      if (len(issues) > 0):
        content = content + "\nNEW ISSUES OF {}: {}".format(repo['link'], ', '.join(map(lambda issue_id: build_single_issue_url(url, issue_id), issues)))
  last_time_checked = datetime.now()
  if (content !=''):
    send_email(from_email, from_password, server, port, to_email, content, subject)
  s.enter(timeout, 1, run)

s.enter(0, 1, run)

s.run(True)

