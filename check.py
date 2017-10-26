import os
import httplib2
from datetime import datetime
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from slackclient import SlackClient
from settings import *
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
                sc.api_call(
                  "chat.postMessage",
                  channel=SLACK_CHANNEL,
                  text="*{0}*\nis happening\n{1} \ndate: {2} \nplace: {3}\n twitter: {4}".format(
                      con[0],
                      conference_db_entry.get('website'),
                      datetime.strftime(conf_date, "%D"),
                      conference_db_entry.get('place'),
                      conference_db_entry.get('twitter'),
                  ),
                )

            db_actions.update_entry(con)

        if db_actions.should_plan(conference_db_entry, conf_date):
            sc.api_call(
                "chat.postMessage",
                channel=SLACK_CHANNEL,
                text="Coming up in four months or so! \n*{0}* \n{1} \n{2}".format(
                    con[0],
                    conference_db_entry.get('website'),
                    datetime.strftime(conf_date, "%D")
                ),
            )


if __name__ == '__main__':
    main()

