from flask import Flask, request, make_response, abort
import os

app = Flask(__name__)
app.config.from_object('settings.dev')
# manual overrides below

# app.config.from_envvar('APP_SETTINGS', silent=True)

@app.route('/')
def hello_world():
    return 'Hello, World!'
    
    
@app.route('/webhook')
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == os.getenv('VERIFY_TOKEN'):
            app.logger.info('Validating Webhook')
            return make_response(request.args.get('hub.challenge'), 200)
        else:
            app.logger.error("Failed validation. Make sure the validation tokens match.")
            abort(403)
    elif request.method == 'POST':
        data = request.get_json()
        if data.get('object') == 'page':
            for entry in data.get('entry', []):
                page_id = entry.get('id')
                time = entry.get('time')
                for event in entry.get('messaging', []):
                    if 'message' in event:
                        recieved_message(event)
                    else:
                        app.logger.warning('Webhook received unknown event: %s', event)
            else:
                app.logger.debug('no more entries...')
                
        make_response('all good!', 200)
        
        
def recieved_message(event):
    app.logger.info("Message Data: %s", event.message)