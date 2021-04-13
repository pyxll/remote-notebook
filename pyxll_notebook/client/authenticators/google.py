"""Authenticator class for connecting to Google AI Platform Notebooks
"""
from .browser_auth import BrowserAuthenticator
from .base import Authenticator
import pyxll
import os


class GoogleAuthenticator(BrowserAuthenticator):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _title(self):
        return "Login to Google"


class GoogleOAuthAuthenticator(Authenticator):

    def __init__(self, credentials, **kwargs):
        super().__init__()
        self.__credentials_file = credentials

    @staticmethod
    def __get_abs_path(path):
        # We don't know the config file name so use the location of the pyxll.xll file
        if path and not os.path.isabs(path):
            return os.path.join(os.path.dirname(pyxll.__file__), path)
        return path

    async def _authenticate(self):
        from google.auth.transport.requests import Request
        from google.auth import load_credentials_from_file

        path = self.__get_abs_path(self.__credentials_file)
        credentials, _ = load_credentials_from_file(path)
        scoped_credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])

        request = Request()
        scoped_credentials.refresh(request)

        headers = {}
        scoped_credentials.apply(headers)

        return {
            "headers": headers,
            "cookies": {}
        }
