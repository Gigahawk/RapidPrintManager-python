
from __future__ import print_function
import httplib2
import os
import io
import time
import datetime
from printJob import *
from settings import *

from googleapiclient.http import MediaIoBaseDownload
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = ['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/spreadsheets.readonly','https://www.googleapis.com/auth/gmail.compose']
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'

#initialize settings
config = settings()

# ID of sheet to monitor
sheetID = None;
discountID = None;
rosterID = None;

# Store the last submission timestamp
lastSubDate = None; 

waitForSheet = None;

# Create a dictionary for fileNames and fileIds
fileDict = {}

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def resetDlFolder():
    from os import listdir
    from os.path import isfile, join

    m_dir = 'temp'
    try:
        os.mkdir(m_dir)
    except FileExistsError:
        print('temp folder already exists')
    tempFiles = [join(m_dir,f) for f in listdir(m_dir) if isfile(join(m_dir,f))]
    for file in tempFiles:
        print("Removing " + file)
        os.remove(file)

def getSheetData(sheetService):
    range = 'Form Responses 1!A2:O'
    sheetRequest = sheetService.spreadsheets().values().get(spreadsheetId = sheetID, range = range).execute()
    return sheetRequest

def formatTime(t):
    return time.strftime("%a, %d %b %Y %H:%M:%S", t)

def formatDateTime(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S")

def parseTime(dateString):
    return time.strptime(dateString, '%m/%d/%Y %H:%M:%S')

def setLastDate(sheetService):
    global lastSubDate
    dateString = config.getString('temp','lastSubDate')
    # Check if value exists in config
    if not dateString:
        print('Can''t find lastSubDate from config file, pulling from drive')
        sheetResponse = getSheetData(sheetService)
        values = sheetResponse.get('values', [])

        if not values:
            print('Warning: no last date found, is the spreadsheet empty?')
            print('Setting lastSubDate to epoch as a fallback...')
            lastSubDate = time.gmtime(0)
            return

        row = values[len(values) - 1]
        dateString = row[0]

    lastSubDate = parseTime(dateString)
    print('set lastSubDate to ' + formatTime(lastSubDate))
    config.setVal('temp','lastSubDate',dateString)

def downloadFile(driveService, id):
    # Pull fileName and remove spaces
    fileName = driveService.files().get(fileId = id).execute().get('name')
    fileName = fileName.replace(' ','').lower()

    print("Downloading " + fileName)
    request = driveService.files().get_media(fileId = id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress()*100))

    with open('./temp/'+fileName, 'wb') as f:
        f.write(fh.getvalue())
    
def getLatestOrders(sheetService, driveService):
    global lastSubDate
    sheetResponse = getSheetData(sheetService)
    values = sheetResponse.get('values', [])
    newOrders = []
    dt = lastSubDate

    if not values:
        print('No spreadsheet data found')
    else: 
        print('Most recent orders')
        for row in values:
            dateString = str(row[0])
            dt = parseTime(dateString)
            if dt > lastSubDate:
                newOrders.append(row)
                print('New order found')
                config.setVal('temp','lastSubDate',dateString)
                resetDlFolder()
                for cell in row:
                    print(str(cell) + ",")

                dlLinks = str(row[12]).split(',')
                for link in dlLinks:
                    id = link.strip()[33:]
                    print('Downloading ' + id)
                    downloadFile(driveService, id)

                temp = printJob(driveService,sheetService,discountID, rosterID, row)


    lastSubDate = dt
    return newOrders

def main():
    # Clean up temp folder
    resetDlFolder()

    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    driveService = discovery.build('drive', 'v3', http=http)

    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    sheetService = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)

    global sheetID
    global discountID
    global rosterID
    global waitForSheet

    sheetID = config.getString('user','sheetID')
    print(config.getString('user','sheetID'))
    discountID = config.getString('user','discountID')
    rosterID = config.getString('user','rosterID')
    waitForSheet = config.getBool('user','waitForSheet')
    print(config.getBool('user','waitForSheet'))
    setLastDate(sheetService)


    # begin with last saved start token for this user or current
    # token from getStartPageToken()
    response = driveService.changes().getStartPageToken().execute()
    savedStartPageToken = response.get('startPageToken')
    pageToken = savedStartPageToken

    print("Start token: " + savedStartPageToken)

    while pageToken is not None:
        request = driveService.changes().list(pageToken=pageToken, spaces='drive')
        changes = request.execute()
        if waitForSheet:
            print('Checking for changes')
            for change in changes.get('changes'):
                fileId = change.get('fileId')
                c_time = change.get('time')
                file = change.get('file')
                fileName = ""
                mimeType = ""
                fullFileExtension = ""
                
                removed = change.get('removed')

                if not removed:
                    fileName = file.get('name')
                    mimeType = file.get('mimeType')
                    fullFileExtension = file.get('fullFileExtension')
                    fileDict[fileId] = fileName
                else:
                    fileDict[fileId] = None

                print("Change found for fileId: " + fileId)
                print("time: " + c_time)
                print("fileName: " + fileName)
                print("fileType: " + str(fullFileExtension))
                print("mimeType: " + mimeType)
                print("deleted: " + str(removed))

                if mimeType == "application/vnd.google-apps.spreadsheet" and fileId == sheetID:
                    print('Spreadsheet has been updated, pulling latest orders...')
                    getLatestOrders(sheetService, driveService)
        else:
            print('Checking spreadsheet')
            getLatestOrders(sheetService, driveService)


        newToken = changes.get('newStartPageToken')
        if newToken is not None:
            # Last page, save this token for next polling interval
            savedStartPageToken = newToken

        if pageToken != savedStartPageToken:
            pageToken = savedStartPageToken
            print("New pageToken: " + pageToken)

        time.sleep(2)

if __name__ == '__main__':
    main()




