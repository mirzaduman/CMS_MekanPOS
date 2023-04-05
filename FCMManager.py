# import firebase_admin
import json
import os
from firebase_admin import credentials, messaging, initialize_app

cred = credentials.Certificate(os.path.expanduser('~/mekanpos_project/serviceAccountKey.json'))
initialize_app(cred)


def send_to_token(token: str, data: dict):
    registration_token = token
    # data_json = json.dumps(data)
    message = messaging.Message(
        data=data,
        token=registration_token
    )

    messaging.send(message)


