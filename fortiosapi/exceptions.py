"""
fortiosapi.exceptions
~~~~~~~~~~~~~~~~~~~
This module contains the set of FortiOSAPI exceptions.
"""

class InvalidLicense(Exception):
    '''
    License invalid.
    '''
    def __init__(self):
        Exception.__init__(self,"License invalid.")


class NotLogged(Exception):
    '''
    Not logged on a session, please login.
    '''
    def __init__(self):
        Exception.__init__(self,"Not logged on a session, please login.")