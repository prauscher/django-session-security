""" Helpers to support json encoding of session data """

from datetime import datetime


def set_last_activity(session, dt):
    """ Set the last activity datetime as a string in the session. """
    session['_session_security'] = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')


def get_last_activity(session):
    """
    Get the last activity datetime string from the session and return the
    python datetime object.
    """
    try:
        return datetime.strptime(session['_session_security'],
                '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        # Sessions written by older versions may lack microseconds.
        try:
            return datetime.strptime(session['_session_security'],
                    '%Y-%m-%dT%H:%M:%S')
        except (ValueError, TypeError):
            return datetime.now()
    except (AttributeError, TypeError):
        # AttributeError: _strptime is a known Python threading bug
        # (http://bugs.python.org/issue7980); fall back gracefully.
        return datetime.now()

