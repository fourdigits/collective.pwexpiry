
from AccessControl import Unauthorized

from collective.pwexpiry.events import InvalidPasswordEntered
from collective.pwexpiry.events import ValidPasswordEntered

from collective.pwexpiry.interfaces import IValidPasswordEntered
from collective.pwexpiry.interfaces import IInvalidPasswordEntered

from plone import api

from plone.registry.interfaces import IRegistry

from zope.component.interfaces import ObjectEvent
from zope.component import queryUtility


def ValidPasswordEntered(user, event):

    registry = queryUtility(IRegistry)
    if not registry:
        return

    # Now check if this user had his account locked
    if user.getProperty('account_locked', False):
        # It was locked, check how much time ago
        locked_date = user.getProperty('account_locked_date')
        disable_time = registry['collective.pwexpiry.disable_time']

        portal = api.portal.get()
        current_time = portal.ZopeTime()
        delta = current_time.asdatetime() - locked_date.asdatetime()
        # We are checking in hours, so we divide in 3600 the elapsed seconds
        if (delta.seconds / 3600) >= disable_time:
            # Enough time has elapsed
            user.setMemberProperties({'account_locked': False,
                                      'password_tries': 0})
        else:
            user.REQUEST.RESPONSE.setHeader('user_disabled', user.getId())
            user.REQUEST.RESPONSE.setHeader(
                'user_disabled_time', (disable_time - (delta.seconds / 3600))
            )
            raise Unauthorized

    else:
        # This account has not been locked, reset current_tries counter
        if user.getProperty('password_tries', 0) > 0:
            user.setMemberProperties({'password_tries': 0})


def InvalidPasswordEntered(user, event):

    # If we are here, means that the provided credentials were invalid

    registry = queryUtility(IRegistry)
    if not registry:
        return

    allowed_tries = registry['collective.pwexpiry.allowed_tries']
    current_tries = user.getProperty('password_tries', 0)

    # Add +1 to the current tries, and lock the account if it went over the
    # limit allowed
    current_tries += 1
    user.setMemberProperties({'password_tries': current_tries})

    if current_tries >= allowed_tries:
        portal = api.portal.get()
        current_time = portal.ZopeTime()
        user.setMemberProperties({'account_locked_date': current_time,
                                  'account_locked': True})
        user.REQUEST.RESPONSE.setHeader('user_disabled', user.getId())
