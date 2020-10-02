import json
import logging
import os
import secrets
import sys
import threading
import time
import uuid
import webbrowser
from urllib.parse import parse_qs, urlparse

import requests

from .flask_app import ServerThread, get_app

logging.getLogger().setLevel(logging.INFO)


# See Application Details here https://www.developer.saxo/openapi/appmanagement#/details/a76c89ba36c9419fb9ff26867241c1bd
# Make sure Redirect URLs is something like http://127.0.0.1:49152/redirect
# See: 
#   https://www.developer.saxo/openapi/learn/oauth-authorization-code-grant
#   https://github.com/SaxoBank/openapi-samples-python/blob/master/authentication/oauth/code-flow/bare-bones-code-flow-app.py
#   https://saxobank.github.io/openapi-samples-js/authentication/oauth2-code-flow/

# See Oauth reference:
# https://www.oauth.com/oauth2-servers/oauth-native-apps/redirect-urls-for-native-apps/
# https://auth0.com/blog/oauth-2-best-practices-for-native-apps/


_CRED_FILENAME = os.path.expanduser("~/.cred/saxo/cred.json")


def get_cred():
    return {x['AppName']: x for x in json.load(open(_CRED_FILENAME))}


def saxo_param_to_oauth_param(**params):
    """saxo gives information in their own format for some reason. Need to map to standard oauth."""
    defaults = {
        'response_type': 'code',
        'state': secrets.token_urlsafe(10),  # generate 10-character string as state
        # 'scope': None, # not used
        'OpenApiBaseUrl': 'https://gateway.saxobank.com/sim/openapi/',
    }
    d = dict()
    d['client_id'] = params['AppKey']
    d['client_secret'] = params['AppSecret']
    d['redirect_uri'] = params['RedirectUrls'][0]
    d['authorization_url'] = params['AuthorizationEndpoint']
    d['token_url'] = params['TokenEndpoint']
    d.update(defaults)
    return d


def get_oauth_param(*, name):
    """ keys in standard oauth format """
    cred = get_cred()[name]
    return saxo_param_to_oauth_param(**cred)


def test_auth(*, name, app=None):
    if app is None:
        app = get_app()
    config = get_oauth_param(name=name)
    res = get_auth_url(**config)
    # config['auth_code'] = res['auth_code'] # not sure this is needed
    logging.info(f"webbrowser open {res['auth_url']}")
    webbrowser.open_new(res['auth_url'])
    token_data = run_server_get_token_data(app, config)

    print('test request user data ... worked as of 2020-10-02')
    a = test_request_user_data(config, token_data)

    print('test refresh token data ... worked as of 2020-10-02')
    b = refresh_new_token_data(config, token_data)
    return config, token_data


def run_server_get_token_data(app, config):
    server = ServerThread(app, config)
    server.start()
    print(f'app._received_callback={app._received_callback}')
    while not app._received_callback:
        try:
            time.sleep(1)
        except KeyboardInterrupt as e:
            print('Caught keyboard interrupt. Shutting down...')
            server.shutdown()
            sys.exit(-1)
    server.shutdown()
    print(f'app._received_callback={app._received_callback}')

    if config['state'] != app._received_state:
        print(
            f'Received state {app._received_state} does not match original state {config["state"]}. Authentication possible compromised.'
        )
        sys.exit(-1)

    if app._error_message:
        print('Received error message. Authentication not successful.')
        print(app._error_message)
        sys.exit(-1)

    config['code'] = app._code

    print('Authentication successful. Requesting token...')

    # pick specific params from the config for post request
    params = {
        'grant_type': 'authorization_code',
        'code': config['code'],
        'redirect_uri': config['redirect_uri'],
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
    }

    res = requests.post(config['token_url'], params=params)

    if res.status_code != 201:
        print('Error occurred while retrieving token. Terminating.')
        sys.exit(-1)

    token_data = res.json()
    print(f'Received token data: {token_data}')
    return token_data


def test_request_user_data(config, token_data):
    print('Requesting user data from OpenAPI...')

    headers = {'Authorization': f"Bearer {token_data['access_token']}"}

    r = requests.get(config['OpenApiBaseUrl'] + 'port/v1/users/me', headers=headers)

    if r.status_code != 200:
        print('Error occurred querying user data from the OpenAPI. Terminating.')

    user_data = r.json()

    return user_data


def refresh_new_token_data(config, token_data):
    print('Using refresh token to obtain new token data...')

    params = {
        'grant_type': 'refresh_token',
        'refresh_token': token_data['refresh_token'],
        'redirect_uri': config['redirect_uri'],
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
    }

    r = requests.post(config['token_url'], params=params)

    if r.status_code != 201:
        print('Error occurred while retrieving token. Terminating.')
        sys.exit(-1)

    print('Received new token data:')
    token_data = r.json()

    return token_data


def get_auth_url(**config):
    params = {
        'response_type': 'code',
        'client_id': config['client_id'],
        'state': config['state'],
        'redirect_uri': config['redirect_uri'],
        'client_secret': config['client_secret'],
    }
    url = config['authorization_url']
    headers = None
    # headers = {"content-type": "application/x-www-form-urlencoded"}
    logging.info(f'requesting {url},\nparams={params},\nheaders={headers}')
    res = requests.get(url, params=params)  # , headers=headers)
    if not res.ok:
        res.raise_for_status()
    else:
        print('received auth data')
    url = urlparse(res.url)
    query = parse_qs(url.query)
    # # extract the URL without query parameters if you need it
    # url_ = url._replace(query=None).geturl()
    auth_code = query['requestId'][0]
    return {'auth_code': auth_code, 'auth_url': res.url}
