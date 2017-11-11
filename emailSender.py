# import httplib2shim
import httplib2
import os

from apiclient import discovery, errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

from time import sleep

from googleapiclient.http import MediaIoBaseUpload

from email.mime.text import *
from email.mime.image import *
from email.mime.audio import *
from email.mime.base import *
from email.mime.multipart import *
# from email import encoders
from email.encoders import encode_base64
import mimetypes
import base64
# import binascii

import io
from io import StringIO

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

    def sendMessage(self, message_str, address, cc, subject, files = []):
        # msg = MIMEText(message_str)
        # msg['to'] = address
        # msg['from'] = self.senderAddress
        # msg['subject'] = "UBC Rapid Printing Service Quote"

        # # Yea i have no fucking clue why you need to encode and then decode
        # rawMsg = {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}

        # try:
        #     message = (self.mailService.users().messages().send(userId="me", body=rawMsg).execute())
        #     print('Message Id: %s' % (message['id']))
        #     return message
        # except errors.HttpError as error:
        #     print('An error occurred: %s' % (error))
        message = MIMEMultipart()
        message['to'] = address
        message['cc'] = cc
        message['from'] = self.senderAddress
        message['subject'] = subject

        msg = MIMEText(message_str)
        message.attach(msg)

        # This line is from google, but it doesnt fucking work
        # rawMsg = {'raw': base64.urlsafe_b64encode(message.as_string())}
        # Yea i have no fucking clue why you need to encode and then decode
        # rawMsg = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        
        # Ok what the actual fuck
        # rawMsg = {'raw': base64.urlsafe_b64encode(message.as_string().encode('UTF-8')).decode('ascii')}

        for file in files:
            content_type, encoding = mimetypes.guess_type(file)
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            main_type, sub_type = content_type.split('/', 1)
            print(main_type)
            print(sub_type)
            if main_type == 'text':
                fp = open(file, 'rb')
                msg = MIMEText(fp.read(), _subtype=sub_type)
                fp.close()
            elif main_type == 'image':
                fp = open(file, 'rb')
                msg = MIMEImage(fp.read(), _subtype=sub_type)
                fp.close()
            elif main_type == 'audio':
                fp = open(file, 'rb')
                msg = MIMEAudio(fp.read(), _subtype=sub_type)
                fp.close()
            else:
                fp = open(file, 'rb')
                msg = MIMEBase(main_type, sub_type)
                msg.set_payload(fp.read())
                encode_base64(msg)
                msg.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file))
                fp.close()
            filename = os.path.basename(file)
            msg.add_header('Content-Disposition', 'attachment', filename=filename)
            message.attach(msg)
        

        if not files:
            print("No attachments, sending small message...")        
            try:
                rawMsg = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
                sendRaw = (self.mailService.users().messages().send(userId="me", body=rawMsg).execute(num_retries=5))
                print('Message Id: %s' % (sendRaw['id']))
                return sendRaw
            except errors.HttpError as error:
                print('An error occurred: %s' % (error))
        else:
            print("Uploading attachments...")
            # rawFiles = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
            # b = io.BytesIO()
            mediafile = StringIO()
            message_bytes = message.as_string() #base64.urlsafe_b64decode(str(rawFiles['raw']))
            mediafile.write(message_bytes)
            media_body = MediaIoBaseUpload(mediafile, mimetype='message/rfc822' )
            print(media_body)
            print(media_body.size())
            print(media_body.mimetype())
            print("Sending large email")

            try:
                sendRaw = (self.mailService.users().messages().send(userId="me", body={}, media_body=media_body).execute(num_retries=5))
                print('Message Id: %s' % (sendRaw['id']))
                return sendRaw
            except errors.HttpError as error:
                print('An error occurred: %s' % (error))

    def get_credentials(self):
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,'gmail-python-quickstart.json')

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