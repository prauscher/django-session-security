Quick setup
===========

The purpose of this documentation is to get you started as fast as possible,
because your time matters and you probably have other things to worry about.

Install the package::

    pip install django-session-security

For static file service, add ``session_security`` to your ``INSTALLED_APPS`` settings:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        'session_security',
        # ...
    ]

Add ``session_security.middleware.SessionSecurityMiddleware`` to your ``MIDDLEWARE`` settings:

.. code-block:: python

    MIDDLEWARE = [
        # ...
        'session_security.middleware.SessionSecurityMiddleware',
        # ...
    ]

.. warning::

    The order of ``MIDDLEWARE`` is important. You should include the ``django-session-security`` middleware
    after the authentication middleware, such as :class:`~django.contrib.auth.middleware.AuthenticationMiddleware`.

Ensure ``django.template.context_processors.request`` is added to the template context processors:

.. code-block:: python

    TEMPLATES = [
        {
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    # ...
                ]
            }
            # ...
        }
    ]

Add ``session_security`` URLs to your project’s URLconf:

.. code-block:: python

    from django.urls import include, path

    urlpatterns = [
        # ...
        path('session_security/', include('session_security.urls')),
    ]

At this point, we're going to assume that you have `django.contrib.staticfiles
<https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/>`_ working.
This means that `static files are automatically served with runserver
<https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#runserver>`_,
and that you have to run `collectstatic when using another server
<https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#collectstatic>`_
(fastcgi, uwsgi, and whatnot). If you don't use `django.contrib.staticfiles`,
then you're on your own to manage staticfiles.

After jQuery, add to your base template::

    {% include 'session_security/all.html' %}

Settings
--------

All settings are optional. Add them to your Django settings file to override
the defaults.

``SESSION_SECURITY_WARN_AFTER`` (default: ``540``)
    Seconds of inactivity before the warning dialog is shown.

``SESSION_SECURITY_EXPIRE_AFTER`` (default: ``600``)
    Seconds of inactivity before the user is logged out.

``SESSION_SECURITY_PASSIVE_URLS``
    List of URL paths the middleware should ignore when tracking activity.

``SESSION_SECURITY_PASSIVE_URL_NAMES``
    Same as ``SESSION_SECURITY_PASSIVE_URLS`` but takes Django URL names.

``SESSION_SECURITY_REDIRECT_TO_LOGOUT`` (default: ``False``)
    When ``True``, an expired session redirects to the logout URL instead of
    reloading the current page. Recommended for SSO setups to avoid silent
    re-authentication. On Django 5.x and above, logout is performed via a
    POST request automatically.

``SESSION_SECURITY_INSECURE`` (default: ``False``)
    Set to ``True`` to allow the app to run without
    ``SESSION_EXPIRE_AT_BROWSER_CLOSE = True``. Not recommended.
