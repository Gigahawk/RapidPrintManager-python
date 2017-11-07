
from __future__ import print_function
import httplib2
import os

from apiclient import discovery, errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

from email.mime.text import *
import base64
import binascii

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

class sender(object):
	senderAddress = "ubcrapidtest@gmail.com"

	def __init__(self):
		self.credentials = self.get_credentials()
		self.http = self.credentials.authorize(httplib2.Http())
		self.mailService = discovery.build('gmail', 'v1', http=self.http)

	def sendMessage(self, message_str, address):
		msg = MIMEText(message_str)
		msg['to'] = address
		msg['from'] = self.senderAddress
		msg['subject'] = "UBC Rapid Printing Service Quote"

		# Yea i have no fucking clue why you need to encode and then decode
		rawMsg = {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}

		try:
		    message = (self.mailService.users().messages().send(userId="me", body=rawMsg).execute())
		    print('Message Id: %s' % (message['id']))
		    return message
		except errors.HttpError as error:
		    print('An error occurred: %s' % (error))


	def get_credentials(self):
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
	                                   'gmail-python-quickstart.json')

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