import requests
import json
import logging
_logger = logging.getLogger(__name__)
import os
import google #pip3 install google-cloud-storage
from google.oauth2 import service_account
import google.auth.transport.requests
SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
FCM_URL = "https://fcm.googleapis.com/v1/projects/"

class FCMAPI(object):

    def __init__(self, auth_file):
        self._PROJECT_KEY_FILE = auth_file

    def _get_access_token(self):
        """Retrieve a valid access token that can be used to authorize requests.
        :return: Access token.
        """
        credentials = service_account.Credentials.from_service_account_file(
        self._PROJECT_KEY_FILE, scopes=SCOPES)
        wrequest = google.auth.transport.requests.Request()
        credentials.refresh(wrequest)
        return credentials.token

    def _headers(self):
        return {
            'Authorization': 'Bearer ' + self._get_access_token(),
            'Content-Type': 'application/json; UTF-8',
        }

    def _push(self, payload):
        file = open(self._PROJECT_KEY_FILE)
        data = json.load(file)
        firebase_project_id = data.get('project_id')
        FCM_URL_v1 = FCM_URL + firebase_project_id + '/messages:send'
        response = requests.post(FCM_URL_v1, headers=self._headers(), data=payload)
        print(response)
        if response.status_code == 200:
            if int(response.headers.get('content-length',0)) <= 0:
                return {}
            return response.json()
        elif response.status_code == 401:
            raise Exception("There was an error authenticating the sender account")
        elif response.status_code == 400:
            raise Exception(response.text)
        else:
            raise Exception("FCM server is temporarily unavailable")

    def send(self, payloads=None):
        self.all_responses = []
        for payload in payloads:
            response = self._push(payload)
            self.all_responses.append(response)
        return self.all_responses

    def jsonDumps(self, data):
        return json.dumps(data).encode('utf8')

    def parse_payload(self, registration_id=None, topic_name=None, message_body=None, message_title=None,
                      message_icon=None, priority=False, data_message=None, badge=None, color=None, tag=None,
                      **extra_kwargs):
        message = dict()
        message['notification'] = {}
        if message_icon:
            message['notification']['icon'] = message_icon
        if message_body:
            message['notification']['body'] = message_body
        if message_title:
            message['notification']['title'] = message_title
        if extra_kwargs:
            message['notification'].update(extra_kwargs)

        if data_message:
            if isinstance(data_message, dict):
                message['data'] = data_message
            else:
                raise Exception("Provided data_message is in the wrong format")
        else:
            message['data'] = message['notification']

        message['android'] = {"notification":{}}
        message['apns'] = {"headers":{},"payload":{"aps":{}}}

        if badge:
            message['android']['notification']['badge'] = badge
            message['apns']['payload']['aps']['badge'] = badge
        if color:
            message['android']['notification']['color'] = color
            message['apns']['payload']['aps']['color'] = color
        if tag:
            message['android']['notification']['tag'] = tag
            message['apns']['payload']['aps']['tag'] = tag
        if priority:
            message['android']['priority'] = 'normal'
            message['apns']['headers']['apns-priority'] = "5"
        else:
            message['android']['priority'] = 'high'
            message['apns']['headers']['apns-priority'] = "10"

        fcm_payload = {"message": message}

        if topic_name:
            message['topic'] = topic_name
        if registration_id:
            message['token'] = registration_id
        return self.jsonDumps(fcm_payload)

if __name__== "__main__":
    #ADD firebase auth JSON file path
    auth_file = os.path.basename('')
    push_service = FCMAPI(auth_file=auth_file)
    # ADD registration_id or fcmToken of any devices related to above firebase project
    registration_id = [""]
    message_title = "Test"
    message_body = "Hi Shivam, your customized news for today is ready!!!"
    for reg_id in registration_id:
        payload = push_service.parse_payload(registration_id=reg_id, message_title=message_title, message_body=message_body)
        print(push_service.send([payload]))
                
