import os
import httplib2
from datetime import datetime
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from slackclient import SlackClient
from credentials.settings import *
import db_actions



try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'credentials/client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'


sc = SlackClient(SLACK_TOKEN)


def get_credentials():
    credential_path = os.path.join('./credentials',
                                   'sheets.googleapis.com-python-quickstart.json')

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
    output_string = "Coming up! " if reason == 'coming_up' else ""
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
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    spreadsheetId = SPREADSHEET_ID

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range="A:Z").execute()

    values = result.get('values', [])
    conferences = values[2:]

    for con in conferences:
        conference_db_entry = db_actions.get_entry(con[0])
        if not conference_db_entry:
            db_actions.create_entry(con)

        else:
            conference_db_entry = db_actions.get_entry(con[0])
            conf_date = datetime.fromtimestamp(db_actions.format_date(con[4])) if len(con) >= 5 else None
            if db_actions.alert_for_change(con, conference_db_entry):
                text = format_slack_message(conference_db_entry, date=conf_date, reason='added')
                sc.api_call(
                  "chat.postMessage",
                  channel=SLACK_CHANNEL,
                  text=text
                )

            db_actions.update_entry(con)

        if db_actions.should_plan(conference_db_entry, conf_date):
            text = format_slack_message(conference_db_entry, date=conf_date, reason='coming_up')
            sc.api_call(
                "chat.postMessage",
                channel=SLACK_CHANNEL,
                text=text
            )


if __name__ == '__main__':
    main()

