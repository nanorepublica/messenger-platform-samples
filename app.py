from flask import Flask, request, make_response, abort
import os
import json
import requests

app = Flask(__name__)
app.config.from_object('settings.dev')
# manual overrides below

# app.config.from_envvar('APP_SETTINGS', silent=True)

@app.route('/')
def hello_world():
    return 'Hello, World!'
    
    
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        subscribe_to_webhook()
    elif request.method == 'POST':
        data = request.get_json()
        if data.get('object') == 'page':
            for entry in data.get('entry', []):
                page_id = entry.get('id')
                time = entry.get('time')
                for event in entry.get('messaging', []):
                    if 'message' in event:
                        recieved_message(event)
                    elif 'postback' in event:
                        receivedPostback(event)
                    else:
                        app.logger.warning('Webhook received unknown event: %s', event)
            app.logger.info('no more entries...')
                
        return make_response('all good!', 200)


def subscribe_to_webhook():
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == os.getenv('VERIFY_TOKEN'):
        app.logger.info('Validating Webhook')
        return make_response(request.args.get('hub.challenge'), 200)
    else:
        app.logger.error("Failed validation. Make sure the validation tokens match.")
        abort(403)


def recieved_message(event):
    app.logger.info("Message Data: %s", event.get('message'))
    
    senderID = event.get('sender', {}).get('id')
    recipientID = event.get('recipient', {}).get('id')
    timeOfMessage = event.get('timestamp')
    message = event.get('message')

    app.logger.info("Received message for user %d and page %d at %d with message:", 
                    senderID, recipientID, timeOfMessage)
    app.logger.info(json.dumps(message))

    messageId = message.get('mid')
    messageText = message.get('text')
    messageAttachments = message.get('attachments')

    message_types = {
        'generic': sendGenericMessage
    }

    if messageText:
        # If we receive a text message, check to see if it matches a keyword
        # and send back the example. Otherwise, just echo the text we received.
        func = message_types.get(messageText, sendTextMessage)
        args = [
            senderID,
            messageText
        ]
        func(*args)
    elif messageAttachments:
        sendTextMessage(senderID, "Message with attachment received")
        

def sendGenericMessage(recipientId, messageText):
    messageData = {
        'recipient': {
            'id': recipientId
        },
        'message': {
            'attachment': {
                'type': "template",
                'payload': {
                    'template_type': "generic",
                    'elements': [
                        {
                            'title': "rift",
                            'subtitle': "Next-generation virtual reality",
                            'item_url': "https://www.oculus.com/en-us/rift/",               
                            'image_url': "http://messengerdemo.parseapp.com/img/rift.png",
                            'buttons': [
                                {
                                    'type': "web_url",
                                    'url': "https://www.oculus.com/en-us/rift/",
                                    'title': "Open Web URL"
                                },
                                {
                                    'type': "postback",
                                    'title': "Call Postback",
                                    'payload': "Payload for first bubble",
                                }
                            ],
                        },
                        {
                            'title': "touch",
                            'subtitle': "Your Hands, Now in VR",
                            'item_url': "https://www.oculus.com/en-us/touch/",
                            'image_url': "http://messengerdemo.parseapp.com/img/touch.png",
                            'buttons': [
                                {
                                    'type': "web_url",
                                    'url': "https://www.oculus.com/en-us/touch/",
                                    'title': "Open Web URL"
                                },
                                {
                                    'type': "postback",
                                    'title': "Call Postback",
                                    'payload': "Payload for second bubble",
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
    callSendAPI(messageData)


def sendTextMessage(recipientId, messageText):
    messageData = {
        'recipient': {
            'id': recipientId
        },
        'message': {
            'text': messageText
        }
    }
    callSendAPI(messageData)


def callSendAPI(messageData):
    uri = 'https://graph.facebook.com/v2.6/me/messages'
    qs = {
        'access_token': os.getenv('PAGE_ACCESS_TOKEN')
    }
    response = requests.post(uri, params=qs, json=messageData)

    if response.ok:
        app.logger.info(response.json())
        # recipientId = response.json().recipient_id
        # messageId = response.json().message_id
        # app.logger.info("Successfully sent generic message with id %s to recipient %s", messageId, recipientId)
    else:
        app.logger.error("Unable to send message.")
        app.logger.error(response)
        app.logger.error(response.content)


def receivedPostback(event):
    senderID = event.get('sender', {}).get('id')
    recipientID = event.get('recipient', {}).get('id')
    timeOfPostback = event.get('timestamp')

    # The 'payload' param is a developer-defined field which is set in a postback 
    # button for Structured Messages.
    payload = event.postback.payload

    app.logger.info("Received postback for user %d and page %d with payload '%s' at %d", 
                    senderID, recipientID, payload, timeOfPostback)

    # When a postback is called, we'll send a message back to the sender to 
    # let them know it was successful
    sendTextMessage(senderID, "Postback called")
