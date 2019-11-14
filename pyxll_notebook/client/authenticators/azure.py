"""Authenticator class for connecting to Azure notebooks
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


class AzureAuthenticator(Authenticator):

    notebooks_url = "https://notebooks.azure.com"
    _use_multiprocessing = True

    def __init__(self, notebooks, azure_user_id=None, azure_project=None, azure_cookie_jar=None, **kwargs):
        super().__init__()
        if not azure_user_id or not azure_project:
            raise AssertionError("azure_user_id and azure_project must be specified.")
        self.__login_clicked = False
        self.__notebooks = notebooks
        self.__user_id = azure_user_id
        self.__project = azure_project
        self.__cookies = {}
        self.__azure_cookie_jar = self.__get_abs_path(azure_cookie_jar)
        self.__load_cookies()

    def __clone_kwargs(self):
        """kwargs to use to create a clone"""
        return {
            "notebooks": self.__notebooks,
            "azure_user_id": self.__user_id,
            "azure_project": self.__project,
            "azure_cookie_jar": self.__azure_cookie_jar,
        }

    @staticmethod
    def __get_abs_path(path):
        # We don't know the config file name so use the location of the pyxll.xll file
        if path and not os.path.isabs(path):
            return os.path.join(os.path.dirname(pyxll.__file__), path)
        return path

    def __load_cookies(self):
        if self.__azure_cookie_jar and os.path.exists(self.__azure_cookie_jar):
            with open(self.__azure_cookie_jar, "rb") as fh:
                _log.debug(f"Loading Azure cookies from {self.__azure_cookie_jar}")
                self.__cookies.update(pickle.load(fh))

    def __save_cookies(self):
        if self.__azure_cookie_jar:
            _log.debug(f"Saving Azure cookies to {self.__azure_cookie_jar}")
            with open(self.__azure_cookie_jar, "wb") as fh:
                pickle.dump(self.__cookies, fh)

    @property
    def __notebook_url(self):
        """Return the URL for one of the configured notebooks.
        This is to login and get the auth token, so any notebook will do.
        """
        notebook = self.__notebooks[0]
        return f"{self.notebooks_url}/{self.__user_id}/projects/{self.__project}/run/notebooks/{notebook}"

    def __on_page_loaded(self, page):
        """Run some Javascript to look for the signin button and click it.
        """
        if not self.__login_clicked:
            from PyQt5.QtWebEngineWidgets import QWebEngineScript

            def callback(clicked):
                self.__login_clicked = clicked

            page.runJavaScript("""
                var login = document.querySelector("a[href='/account/signin#']");
                var clicked = 0;
                if (login) {
                    login.click();
                    clicked = 1;
                }
                clicked;
            """, QWebEngineScript.ApplicationWorld, callback)

    def __on_cookie_added(self, got_auth_event, cookie):
        """Add cookies to our cookie jar.
        """
        key = cookie.name().data().decode()
        cookies = aiohttp.cookiejar.SimpleCookie(cookie.toRawForm().data().decode())
        self.__cookies[key] = cookies[key]

        # Once we've got the auth token we can stop
        if key == "_xsrf":
            _log.debug("Got authentication token from Azure.")
            got_auth_event.set()

    def __update_cookie_store(self, cookie_store):
        from PyQt5.QtNetwork import QNetworkCookie
        from PyQt5.QtCore import QByteArray

        for key, cookie in self.__cookies.items():
            # Skip the auth token as we'll get it again after a successful login
            if key == "_xsrf":
                continue

            # Add the cookie to store
            value = str(cookie)
            if ":" in value:
                value = value.split(":", 1)[1].strip()
            for morsel in QNetworkCookie.parseCookies(QByteArray(value.encode("utf-8"))):
                cookie_store.setCookie(morsel)

    async def _alogin(self):
        """async login method."""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
        from PyQt5.QtCore import QEventLoop, QUrl

        app = QApplication(sys.argv)
        browser = QWebEngineView()
        profile = QWebEngineProfile()
        page = QWebEnginePage(profile, browser)

        loop = asyncio.get_event_loop()
        browser_closed_event = asyncio.Event(loop=loop)
        page.windowCloseRequested.connect(lambda event: browser_closed_event.set())

        # whenever a page finishes loading, look for the login button
        page.loadFinished.connect(partial(self.__on_page_loaded, page))

        # keep track of cookies
        cookies = profile.cookieStore()
        self.__update_cookie_store(cookies)
        got_auth_event = asyncio.Event(loop=loop)
        cookies.cookieAdded.connect(partial(self.__on_cookie_added, got_auth_event))

        # navigate to the notebook and show the browser
        page.setUrl(QUrl(self.__notebook_url))
        browser.setPage(page)
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
        """Present a browser to the user to login to azure."""
        # Do the login in a child process as Qt won't run properly from a background thread
        # (and it avoids problems with multiple QApplication instances in the main process)
        if self._use_multiprocessing:
            with ProcessPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                cookies = await loop.run_in_executor(executor, partial(self._mp_login, **self.__clone_kwargs()))
                self.__cookies.update(cookies)
        else:
            await self._alogin()

        self.__save_cookies()

    async def _authenticate(self):
        await self.login()

        return {
            "headers": {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-XSRFToken": self.__cookies["_xsrf"].value,
            },
            "cookies": self.__cookies
        }

    def reset(self):
        super().reset()
        if self.__azure_cookie_jar and os.path.exists(self.__azure_cookie_jar):
            os.unlink(self.__azure_cookie_jar)
