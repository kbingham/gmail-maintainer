#!/usr/bin/env python3

# Copyright 2018 Google LLC
# Copyright 2020 Linux Embedded Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class Message:
    def __init__(self, message):
        self.headers = {}
        for h in message['payload']['headers']:
            self.headers[h['name']] = h['value']

        self.Subject = self.headers['Subject']
        self.From = self.headers['From']

    def __str__(self):
        return f"{self.headers['Subject']} ({self.headers['From']})"


class Thread:
    def __init__(self, service, thread):
        '''
            {
             'id': '175cdc40da51800f',
             'snippet': '<leading mail text>',
             'historyId': '7563335'
            }
        '''
        self.service = service
        self.thread = thread
        self.id = thread['id']
        self.tdata = service.users().threads().get(userId='me', id=thread['id']).execute()

        self.messages = []

        for msg in self.tdata['messages']:
            self.messages.append(Message(msg))

    def __str__(self):
        return str(self.messages[0])


class Gmail:
    # If modifying these scopes, delete the file token.pickle.
    scopes = ['https://www.googleapis.com/auth/gmail.readonly']
    labels_ = {}

    def __init__(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.scopes)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)

    def labels(self):
        if not self.labels_:
            # Call the Gmail API
            results = self.service.users().labels().list(userId='me').execute()
            label_results = results.get('labels', [])

            if not label_results:
                print('No labels found.')
            else:
                for label in label_results:
                    self.labels_[label['name']] = label

        return self.labels_

    def label(self, l):
        return self.labels()[l]

    def threads(self, label):
        response = self.service.users().threads().list(userId='me',
                                                       labelIds=label['id']).execute()
        threads = []
        threads.extend(response['threads'])

        for thread in threads:
            yield Thread(self.service, thread)
