"""Authenticator class for connecting to Google AI Platform Notebooks
"""
from .browser_auth import BrowserAuthenticator


class GoogleAuthenticator(BrowserAuthenticator):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _title(self):
        return "Login to Google"
