import secrets
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse

import requests
from flask import Flask, current_app, request
from werkzeug.serving import make_server


def get_app():
    app = Flask('saxo_auth_app')
    app._received_callback = None
    app._code = None
    app._error_message = None
    app._received_state = None

    @app.route(
        '/redirect'
    )  # saxo example has /callback here but not sure if that needs to appear elsewhere or is it added?
    def handle_callback():
        current_app._render_text = None

        if 'error' in request.args:
            current_app._error_message = request.args['error'] + ': ' + request.args['error_description']
            current_app._render_text = 'Error occurred. Please check the application command line.'
        else:
            print(f'request.args is {request.args}')
            try:
                current_app._code = request.args['code']
                current_app._received_state = request.args['state']
                current_app._render_text = 'Please return to the application.'
            except KeyError as e:
                current_app._render_text = f'Error occurred. Missing argument in callback {e}'
        current_app._received_callback = True
        return current_app._render_text

    return app


def get_test_app():
    app = Flask('test_app')
    app._received_callback = None

    @app.route('/')
    def hello_world():
        current_app._received_callback = True
        return 'Hello, World!'

    return app


class ServerThread(threading.Thread):
    """
    The Flask server will run inside a thread so it can be shut down when the callback is received.
    The server is automatically configured on the host and port specified in the configuarion dictionary.
    """

    def __init__(self, app, config):
        threading.Thread.__init__(self)
        url = urlparse(config['redirect_uri'])
        host = url.hostname
        port = url.port
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        print(f'Starting server on {self.server.host}:{self.server.port} and listen for callback from Saxo...')
        self.server.serve_forever()

    def shutdown(self):
        print('Terminating server...')
        self.server.shutdown()


def test_basic(test_app=True):
    # basic test to just hit the server and see if it parses
    if test_app:
        app = get_test_app()
    else:
        app = get_app()
    config = dict(redirect_uri='http://localhost:5678')
    server = ServerThread(app, config)
    server.start()
    print(f'app._received_callback={app._received_callback}')
    res = requests.get(config['redirect_uri'], params={'code': 'something', 'state': secrets.token_urlsafe(10)})
    print(f'GET: {res.url} returned {res.text}')
    print(f'app._received_callback={app._received_callback}')
    while not app._received_callback:
        try:
            time.sleep(1)
        except KeyboardInterrupt as e:
            print('Caught keyboard interrupt. Shutting down...')
            server.shutdown()
            sys.exit(-1)
    server.shutdown()
