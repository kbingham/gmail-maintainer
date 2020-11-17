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

import json
import pickle
import sqlite3
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class DbCache:
    def __init__(self):
        dbpath = 'cache.db'
        db_exists = os.path.isfile(dbpath)

        self.c = sqlite3.connect(dbpath)
        self.cursor = self.c.cursor()

        if not db_exists:
            self.create_tables()
            self.commit()

    def commit(self):
        self.c.commit()

    def create_tables(self):
        self.cursor.execute('''
        CREATE TABLE threads (
            id TEXT,
            data json
            )
        ''')

    def getThreadData(self, tid):
        ret = self.cursor.execute('''
            SELECT data FROM threads WHERE id=?
        ''', (tid, )).fetchall()

        if not ret:
            return []

        return json.loads(ret[0][0])

    def saveThreadData(self, tid, tdata):
        self.cursor.execute('''
            INSERT INTO threads VALUES(?, ?)
        ''', (tid, json.dumps(tdata)))

        self.commit()


d = DbCache()


class Message:
    def __init__(self, message):
        self.headers = {}
        for h in message['payload']['headers']:
            self.headers[h['name']] = h['value']

        self.Subject = self.headers['Subject']
        self.From = self.headers['From']
        self.labels = message['labelIds']

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
        self.historyId = thread['historyId']

        # Load data from cache if available, or Gmail otherwise.
        self.tdata = d.getThreadData(self.id)
        if not self.tdata:
            self.tdata = service.users().threads().get(userId='me',
                                                       id=self.id,
                                                       format='metadata').execute()
            d.saveThreadData(self.id, self.tdata)

        self.messages = []
        for msg in self.tdata['messages']:
            self.messages.append(Message(msg))

        self.subject = self.messages[0].Subject

    def modify(self, removeLabels, addLabels):
        toModify = {
                    "removeLabelIds": [l.id for l in removeLabels],
                    "addLabelIds": [l.id for l in addLabels],
        }
        return self.service.users().threads().modify(userId='me',
                                                     id=self.id,
                                                     body=toModify).execute()

    def addLabel(self, label):
        return self.modify([], [label])

    def removeLabel(self, label):
        return self.modify([label], [])

    def labels(self):
        messageLabels = set()
        for m in self.messages:
            messageLabels.update(m.labels)

        return messageLabels

    def __str__(self):
        return str(self.messages[0])

    def raw(self):
        return self.thread


class Label:
    def __init__(self, label):
        self.label = label
        self.name = label['name']
        self.id = label['id']

    def __str__(self):
        return str(self.name + ' : (' + self.id + ')')

    def __repr__(self):
        return str(self)


class ThreadPage:
    def __init__(self, service, label, pageToken=None):
        if pageToken:
            response = service.users().threads().list(userId='me',
                                                      labelIds=label.id,
                                                      pageToken=pageToken).execute()
        else:
            response = service.users().threads().list(userId='me',
                                                      labelIds=label.id).execute()
        self.threads_ = []
        self.threads_ = response['threads'].copy()
        self.resultSizeEstimate = response['resultSizeEstimate']
        if 'nextPageToken' in response:
            self.nextPageToken = response['nextPageToken']
        else:
            self.nextPageToken = False

    def threads(self):
        for thread in self.threads_:
            yield thread


class Gmail:
    # Changing the scopes will require re-authentication, with a new token.
    scopes = ['https://www.googleapis.com/auth/gmail.modify']
    labels_ = {}

    def __init__(self):
        creds = None
        # The token file stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the
        # first time. Any change to the scopes will generate a new token file.
        token_file = 'token.' + os.path.basename(self.scopes[0])
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
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
            with open(token_file, 'wb') as token:
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
                    self.labels_[label['name']] = Label(label)

        return self.labels_

    def label(self, l):
        return self.labels()[l]

    def threads(self, label):
        tpage = ThreadPage(self.service, label)
        for thread in tpage.threads():
            yield Thread(self.service, thread)

        while tpage.nextPageToken:
            tpage = ThreadPage(self.service, label, tpage.nextPageToken)
            for thread in tpage.threads():
                yield Thread(self.service, thread)
