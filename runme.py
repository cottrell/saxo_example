#!/usr/bin/env python
from auth import get_cred, test_auth

if __name__ == '__main__':
    import argh

    argh.dispatch_commands([test_auth, get_cred])
