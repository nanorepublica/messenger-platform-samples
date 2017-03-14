'hello world messenger bot'
import os
from functools import wraps
import json
import requests
from flask import Flask, request, make_response, abort

app = Flask(__name__)
app.config.from_object('settings.dev')
# manual overrides below

# app.config.from_envvar('APP_SETTINGS', silent=True)


@app.route('/')
def hello_world():
    '''index page - should explain/document the bot?'''
    return 'Hello, World!'


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    'webhook endpoint'
    if request.method == 'GET':
        return subscribe_to_webhook()
    elif request.method == 'POST':
        return process_webhook()


def subscribe_to_webhook():
    '''subscribe to the webhook on facebook'''
    if (request.args.get('hub.mode') == 'subscribe' and
            request.args.get('hub.verify_token') == os.getenv('VERIFY_TOKEN')):
        app.logger.info('Validating Webhook')
        return make_response(request.args.get('hub.challenge'), 200)
    else:
        app.logger.error("Failed validation. Make sure the validation tokens match.")
        abort(403)


def process_webhook():
    '''process the response from the webhook post response'''
    data = request.get_json()
    if data.get('object') == 'page':
        for entry in data.get('entry', []):
            # page_id = entry.get('id')
            # time = entry.get('time')
            for event in entry.get('messaging', []):
                if 'message' in event:
                    recieved_message(event)
                elif 'postback' in event:
                    received_postback(event)
                else:
                    app.logger.warning('Webhook received unknown event: %s', event)
        app.logger.info('no more entries...')
    return make_response('all good!', 200)


def send(func):
    'decorator to send a message to the graph API'
    @wraps(func)
    def _inner(*args, **kwargs):
        'inner function'
        if 'recipient_id' in kwargs:
            recipient_data = {
                'id': kwargs.get('recipient_id')
            }
        message_data = func(*args, **kwargs)
        if 'recipient_id' in kwargs:
            message_data['recipient'] = recipient_data
            call_send_api(message_data)
    return _inner


def call_send_api(message_data):
    '''call send api and handle the response'''
    uri = 'https://graph.facebook.com/v2.6/me/messages'
    query_string = {
        'access_token': os.getenv('PAGE_ACCESS_TOKEN')
    }
    response = requests.post(uri, params=query_string, json=message_data)

    if response.ok:
        app.logger.error(response.json())
        # recipient_id = response.json().recipient_id
        # message_id = response.json().message_id
        # app.logger.info("Successfully sent generic message with id %s to recipient %s",
        #                 message_id, recipient_id)
    else:
        app.logger.error("Unable to send message.")
        app.logger.error(response)
        app.logger.error(response.content)


@send
def send_generic_message(*_args, **_kwargs):
    'todo: improve - send a templated message'
    return {
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


@send
def send_text_message(*args, **kwargs):
    '''send a simple text message'''
    return {
        'message': {
            'text': kwargs.get('message_text')
        }
    }


def recieved_message(event):
    '''decision tree on what message to reply with...'''
    app.logger.info("Message Data: %s", event.get('message'))

    sender_id = event.get('sender', {}).get('id')
    recipient_id = event.get('recipient', {}).get('id')
    time_of_message = event.get('timestamp')
    message = event.get('message')

    app.logger.info("Received message for user %d and page %d at %d with message:",
                    sender_id, recipient_id, time_of_message)
    app.logger.info(json.dumps(message))

    # message_id = message.get('mid')
    message_text = message.get('text')
    message_attachments = message.get('attachments')

    message_types = {
        'generic': send_generic_message
    }

    if message_text:
        # If we receive a text message, check to see if it matches a keyword
        # and send back the example. Otherwise, just echo the text we received.
        print send_text_message
        message_func = message_types.get(message_text, send_text_message)
        args = [
            sender_id,
            message_text
        ]
        print args, message_func
        message_func(*args)
    elif message_attachments:
        send_text_message(message_text="Message with attachment received", recipient_id=sender_id)


def received_postback(event):
    '''process postback response from the bot'''
    sender_id = event.get('sender', {}).get('id')
    recipient_id = event.get('recipient', {}).get('id')
    time_of_postback = event.get('timestamp')

    # The 'payload' param is a developer-defined field which is set in a postback
    # button for Structured Messages.
    payload = event.get('postback', {}).get('payload')

    app.logger.info("Received postback for user %d and page %d with payload '%s' at %d",
                    sender_id, recipient_id, payload, time_of_postback)

    # When a postback is called, we'll send a message back to the sender to
    # let them know it was successful
    send_text_message(message_text="Postback called", recipient_id=sender_id)
