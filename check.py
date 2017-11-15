import os
import httplib2
from datetime import datetime
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from slackclient import SlackClient
import db_actions

# set keys for heroku
if os.environ.get('ENV', '') == 'heroku':
    DISCOVERY_URL = os.environ.get('DISCOVERY_URL')
    DISCOVERY_URL_VERSION = os.environ.get('DISCOVERY_URL_VERSION')
    SCOPES = os.environ.get('SCOPES')
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
    CLIENT_SECRET_FILE = os.environ.get('CLIENT_SECRET_FILE')
    SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL')
    SLACK_TOKEN = os.environ.get('SLACK_TOKEN')
    APPLICATION_NAME = os.environ.get('APPLICATION_NAME')
else:
    # set keys everywhere else
    from settings import *

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

sc = SlackClient(SLACK_TOKEN)


def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def format_slack_message(entry, date=None, reason='added'):
    name = entry.get('name')
    website = entry.get('website')
    twitter = entry.get('twitter')
    place = entry.get('place')

    if reason == 'coming_up':
        output_string = "Coming up: "
    elif reason == 'added':
        output_string = "Just added: "
    elif reason == 'date_change':
        output_string = "Date change: "
    else:
        output_string = ""

    output_string += "*" + name + "*"
    if website:
        output_string += "\n" + website
    if twitter:
        output_string += "\n" + twitter
    if place:
        output_string += "\nlocation: " + place
    if date:
        output_string += "\ndate: " + datetime.strftime(date, "%D")

    return output_string


def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discovery_url = DISCOVERY_URL + DISCOVERY_URL_VERSION
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discovery_url)

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="A:Z").execute()

    values = result.get('values', [])

    # first line is column headers
    conferences = values[1:]

    kwargs = {
        'channel': SLACK_CHANNEL,
        'username': 'confbot',
        'unfurl_links': True,
        'icon_emoji': ":rabbit2:",
    }

    for con in conferences:
        conference_db_entry = db_actions.get_entry(con[0])
        if not conference_db_entry:
            conference_db_entry = db_actions.create_entry(con)
            conf_date = datetime.fromtimestamp(db_actions.format_date(con[4])) if len(con) >= 5 else None
            text = format_slack_message(conference_db_entry, date=conf_date, reason='added')
            sc.api_call("chat.postMessage", text=text, **kwargs)
        else:
            conf_date = datetime.fromtimestamp(db_actions.format_date(con[4])) if len(con) >= 5 else None
            if db_actions.alert_for_change(con, conference_db_entry):
                text = format_slack_message(conference_db_entry, date=conf_date, reason='date_change')
                sc.api_call("chat.postMessage", text=text, **kwargs)

            db_actions.update_entry(con)

        if db_actions.should_plan(conference_db_entry, conf_date):
            text = format_slack_message(conference_db_entry, date=conf_date, reason='coming_up')
            sc.api_call("chat.postMessage", text=text, **kwargs)

if __name__ == '__main__':
    main()

