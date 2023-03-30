# import firebase_admin
import os
from firebase_admin import credentials, messaging, initialize_app

cred = credentials.Certificate(os.path.expanduser('~/PycharmProjects/mekanpos/serviceAccountKey.json'))
initialize_app(cred)


def send_to_token(token: str, title: str, body: str):
    registration_token = token

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=registration_token,
    )

    messaging.send(message)


