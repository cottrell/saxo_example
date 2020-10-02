# Saxo Example API connectivity

Example connectivity with Saxo.

## Manual setup

See the steps here https://www.developer.saxo/openapi/learn/writing-an-openapi-application.

Note that you really need to apply for an application to the live environment to actually test anything to do with data that you pay for since there is no way to link your account to a vanilla demo account and obtain actual data feeds.

Create a Simulation App here https://www.developer.saxo/openapi/appmanagement#/ with a redirect URL something like this:

    http://127.0.0.1:49152/redirect

Navigate to the Application Detail and copy the app object (json) and add entry to a json list stored at `~/.cred/saxo/cred.json`.

## Oauth

Example script that worked as of 2020-10-02.

Inspired by the example sketch here https://github.com/SaxoBank/openapi-samples-python/blob/master/authentication/oauth/code-flow/bare-bones-code-flow-app.py.

```bash
    pip install -r requirements.pip
    ./runme.py get-cred  # test cred.json reading works and list names of apps in cred.json
    ./runme.py test-auth --name APPNAME  # should run without error and print things
```

Better yet run from IPython REPL for debugging experience:

```python
    In [1]: import auth as a
    In [2]: a.test_auth(name='ONEOFYOURAPPNAMESINCREDJSON')
```
