"""Base class for browser based authentication.
"""
from .base import Authenticator
from ...errors import AuthenticationError
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import aiohttp.cookiejar
import asyncio
import logging
import pickle
import pyxll
import sys
import os

_log = logging.getLogger(__name__)


class BrowserAuthenticator(Authenticator):

    # Set to False to do everything in a single process.
    _use_multiprocessing = True

    def __init__(self, url, cookie_jar_path=None, **kwargs):
        super().__init__()
        self.__url = url
        self.__cookie_jar_path = cookie_jar_path
        self.__cookies = {}
        self.__load_cookies()

    def _title(self):
        """Return the title for the browser window."""
        raise NotImplemented("_title must be implemented by the subclass")

    def _login_url(self):
        """Return the url for the login page."""
        return self.__url

    def _extra_kwargs(self):
        """extra kwargs to use to create a clone not used by the base class."""
        return {}

    def _auth_cookie_name(self):
        """Name of the cookie to look for to confirm successful login."""
        return "_xsrf"

    def _on_page_loaded(self, browser, *args):
        """Callback for when a page is loaded."""
        pass

    def _cookie_jar_path(self):
        """Return the path to the cookie jar, or None"""
        return self.__cookie_jar_path

    @staticmethod
    def __get_abs_path(path):
        # We don't know the config file name so use the location of the pyxll.xll file
        if path and not os.path.isabs(path):
            return os.path.join(os.path.dirname(pyxll.__file__), path)
        return path

    def __load_cookies(self):
        cookie_jar_path = self.__get_abs_path(self._cookie_jar_path())
        if cookie_jar_path and os.path.exists(cookie_jar_path):
            with open(cookie_jar_path, "rb") as fh:
                _log.debug(f"Loading cookies from {cookie_jar_path}")
                self.__cookies.update(pickle.load(fh))

    def __save_cookies(self):
        cookie_jar_path = self.__get_abs_path(self._cookie_jar_path())
        if cookie_jar_path:
            _log.debug(f"Saving cookies to {cookie_jar_path}")
            if not os.path.exists(os.path.dirname(cookie_jar_path)):
                os.makedirs(cookie_jar_path)
            with open(cookie_jar_path, "wb") as fh:
                pickle.dump(self.__cookies, fh)

    def __on_cookie_added(self, got_auth_event, auth_cookie_name, cookie):
        """Add cookies to our cookie jar."""
        key = cookie.name().data().decode()
        cookies = aiohttp.cookiejar.SimpleCookie(cookie.toRawForm().data().decode())
        self.__cookies[key] = cookies[key]

        # Once we've got the auth token we can stop
        if key == auth_cookie_name:
            _log.debug("Got authentication token.")
            got_auth_event.set()

    def __update_cookie_store(self, cookie_store):
        from .widgets.qtimports import QNetworkCookie, QByteArray

        auth_cookie_name = self._auth_cookie_name()
        for key, cookie in self.__cookies.items():
            # Skip the auth token as we'll get it again after a successful login
            if key == auth_cookie_name:
                continue
            print(f"{key} = {cookie}")

            # Add the cookie to store
            value = str(cookie)
            if ":" in value:
                value = value.split(":", 1)[1].strip()
            for morsel in QNetworkCookie.parseCookies(QByteArray(value.encode("utf-8"))):
                cookie_store.setCookie(morsel)

    async def _alogin(self):
        """async login method."""
        from .widgets.qtimports import QApplication, QEventLoop
        from .widgets.browser import Browser

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        title = self._title()
        browser = Browser(title)

        loop = asyncio.get_event_loop()
        browser_closed_event = asyncio.Event(loop=loop)
        browser.windowCloseRequested.connect(lambda *args: browser_closed_event.set())

        # whenever a page finishes loading, look for the login button
        browser.loadFinished.connect(partial(self._on_page_loaded, browser))

        # keep track of cookies
        cookies = browser.cookieStore()
        self.__update_cookie_store(cookies)
        got_auth_event = asyncio.Event(loop=loop)
        auth_cookie_name = self._auth_cookie_name()
        cookies.cookieAdded.connect(partial(self.__on_cookie_added, got_auth_event, auth_cookie_name))

        # navigate to the login page and show the browser
        url = self._login_url()
        browser.setUrl(url)
        browser.show()

        # process Qt events until we've got the token or the browser is closed
        async def poll():
            future = asyncio.gather(got_auth_event.wait(), browser_closed_event.wait())
            while not got_auth_event.is_set() and not browser_closed_event.is_set():
                app.processEvents(QEventLoop.AllEvents, 300)
                await asyncio.wait([future], loop=loop, timeout=0)

        await poll()

        if not got_auth_event.is_set():
           raise AuthenticationError()

        return self.__cookies

    @classmethod
    def _mp_login(cls, **kwargs):
        """Entry point for doing login in a child process."""
        auth = cls(**kwargs)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(auth._alogin())

    async def login(self):
        """Present a browser to the user to login."""
        # Do the login in a child process as Qt won't run properly from a background thread
        # (and it avoids problems with multiple QApplication instances in the main process)
        kwargs = {"url": self.__url, "cookie_jar_path": self.__cookie_jar_path}
        kwargs.update(self._extra_kwargs())
        if self._use_multiprocessing:
            with ProcessPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                cookies = await loop.run_in_executor(executor, partial(self._mp_login, **kwargs))
                self.__cookies.update(cookies)
        else:
            await self._alogin()

        self.__save_cookies()

    async def _authenticate(self):
        await self.login()
        auth_cookie_name = self._auth_cookie_name()
        return {
            "headers": {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-XSRFToken": self.__cookies[auth_cookie_name].value
            },
            "cookies": self.__cookies
        }

    def reset(self):
        super().reset()
        cookie_jar_path = self.__get_abs_path(self._cookie_jar_path())
        if cookie_jar_path and os.path.exists(cookie_jar_path):
            os.unlink(cookie_jar_path)
