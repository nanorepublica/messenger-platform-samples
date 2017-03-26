'''
message = Message()
message.text = 'Hello world'
message.send()
'''
import os
import logging
import requests

from messenger.exceptions import NoPageAccessToken, NoRecipientException, NoContentException

logger = logging.getLogger(__name__)


class SendAPI(object):
    'api stuff'
    notification_types = {
        'regular': 'REGULAR',
        'silent_push': 'SILENT_PUSH',
        'no_push': 'NO_PUSH'
    }
    _notify_type = 'regular'
    _message = None
    _sender_action = None
    _recipient = {
        'id': None
    }

    def __init__(self, recipient_id=None, access_token=None):
        if access_token:
            self.access_token = access_token
        elif 'PAGE_ACCESS_TOKEN' in os.environ.keys():
            self.access_token = os.getenv('PAGE_ACCESS_TOKEN')
        else:
            self.access_token = None
            raise NoPageAccessToken()
        if recipient_id:
            self.recipient_id = recipient_id

    @property
    def recipient(self):
        'TODO: add phone number and name for customer matching'
        return self._recipient.get('id')

    @recipient.setter
    def recipient(self, value):
        self._recipient['id'] = value

    @property
    def notification_type(self):
        'get the notification type'
        return self.notification_types.get(self._notify_type, 'REGULAR')

    @notification_type.setter
    def notification_type(self, value):
        self._notify_type = value

    @property
    def message(self):
        'content of the message'
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    @property
    def sender_action(self):
        'content of the sender action'
        return self._sender_action

    @sender_action.setter
    def sender_action(self, value):
        self._sender_action = value

    @property
    def payload(self):
        'return the constructed payload to send to the API'
        _payload = {
            'recipient': self._recipient,
        }
        if self.notification_type:
            _payload['notification_type'] = self.notification_type
        if self.message:
            _payload['message'] = self.message
            return _payload
        if self.sender_action:
            _payload['sender_action'] = self.sender_action
            return _payload

    def call_api(self):
        'wrapped to call api with the payload above'
        print(self.payload)
        return self.call_send_api_raw(self.payload)

    def call_send_api_raw(self, message_data):
        '''call send api and handle the response'''
        uri = 'https://graph.facebook.com/v2.6/me/messages'
        query_string = {
            'access_token': self.access_token
        }
        response = requests.post(uri, params=query_string, json=message_data)

        # TODO: handle better!
        if response.ok:
            logger.error(response.json())
            # recipient_id = response.json().recipient_id
            # message_id = response.json().message_id
            # app.logger.info("Successfully sent generic message with id %s to recipient %s",
            #                 message_id, recipient_id)
            return response.json()
        else:
            logger.error("Unable to send message.")
            logger.error(response)
            logger.error(response.content)


class SenderAction(SendAPI):
    'manager sender actions'
    _mark_seen, _typing_on, _typing_off = False, False, False

    def getter(self, name):
        'get a value'
        return getattr(self, name)

    def setter(self, name, value):
        'setting a value of a property'
        setattr(self, name, bool(value))
        if getattr(self, name):
            self.sender_action = name[1:]
            self.call_api()

    @property
    def mark_seen(self):
        'mark_seen sender action'
        return self.getter('_mark_seen')

    @mark_seen.setter
    def mark_seen(self, value):
        self.setter('_typing_on', not value)
        self.setter('_typing_off', not value)
        self.setter('_mark_seen', value)

    @property
    def typing_on(self):
        'typing_on sender action'
        return self.getter('_typing_on')

    @typing_on.setter
    def typing_on(self, value):
        self.setter('_typing_off', not value)
        self.setter('_mark_seen', not value)
        self.setter('_typing_on', value)

    @property
    def typing_off(self):
        'typing_off sender action'
        return self.getter('_typing_off')

    @typing_off.setter
    def typing_off(self, value):
        self.setter('_typing_on', not value)
        self.setter('_mark_seen', not value)
        self.setter('_typing_off', value)


class Message(object):
    'Basic Message class'
    _message = None

    def __init__(self):
        self.client = SendAPI()

    def set_recipient(self, recipient_id):
        'set the recipient for the message'
        self.client.recipient = recipient_id

    def send(self, recipient=None):
        'send a message!'
        if recipient:
            self.set_recipient(recipient)
        elif self.client.recipient is None:
            raise NoRecipientException()
        assert 'text' in self.message or 'attachment' in self.message, 'Please specify either text or an attachment in the message'
        assert not('text' in self.message and 'attachment' in self.message), 'text and attachment are mutually exclusive, please specify only one'
        self.client.message = self.message
        self.client.call_api()
        return self

    @property
    def message(self):
        'return formatted message held in private variable'
        return self._message

    @message.setter
    def message(self, value):
        'Implement in subclass'
        self.set_message(value)

    def set_message(self, value):
        raise NotImplementedError


class TextMessage(Message):
    'Text message'
    text = None

    def __init__(self, text=None):
        super().__init__()
        if text:
            self.text_message = text
        elif self.text:
            self.text_message = self.text
        else:
            raise NoContentException()

    def set_message(self, value):
        'Used in the .message property'
        self._message = {
            'text': value
        }

    @property
    def text_message(self):
        'get the text value of the message'
        return self._message.get('text', '')

    @text_message.setter
    def text_message(self, value):
        self.message = value


class AttachmentMessage(Message):
    'attachment message'
    _type = None
    is_reusable = False
    payload = None

    def __init__(self, payload=None):
        super().__init__()
        if isinstance(payload, str):
            self.is_reusable = True
        if payload:
            self.attachment = payload
        elif self.payload:
            self.attachment = self.payload
        else:
            raise NoContentException()

    def set_message(self, value):
        'Used in the .message property'
        self._message = {
            'attachment': value
        }

    @property
    def attachment(self):
        'get the text value of the message'
        return self._message.get('attachment', {})

    @attachment.setter
    def attachment(self, value):
        if self.is_reusable:
            self.message = {
                'type': self._type,
                'payload': {
                    'attachement_id': value
                }
            }
        else:
            self.message = {
                'type': self._type,
                'payload': value
            }


class ImageMessage(AttachmentMessage):
    'image message'
    _type = 'image'


class VideoMessage(AttachmentMessage):
    'video message'
    _type = 'video'


class AudioMessage(AttachmentMessage):
    'send audio'
    _type = 'audio'


class FileMessage(AttachmentMessage):
    'send a file'
    _type = 'file'


class TemplateMessage(AttachmentMessage):
    'generic template'
    _type = 'template'


class ButtonTemplateMessage(TemplateMessage):
    'button template message'
    pass

# etc...

# define messages
# sender actions?
# triggers - time, incoming messages
# define flows from that
