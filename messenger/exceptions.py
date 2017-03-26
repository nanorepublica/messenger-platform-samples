'Messenger Exceptions'


class NoPageAccessToken(BaseException):
    'Exception raised when no access token provided'
    message = 'No access token provided to make API calls'


class NoRecipientException(BaseException):
    'Raised when a message has no recipient set when trying to send a message'
    message = 'No recipient set for this message, set one before trying to send a message'


class NoContentException(ValueError):
    'Raised when a message is created without the appropriate content'
    message = 'No content has been set for this message'
