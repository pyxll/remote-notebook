"""Authenticator for Jupyter servers requiring no authentication.
"""
from .base import Authenticator


class NoAuthAuthenticator(Authenticator):

    def __init__(self, **kwargs):
        super().__init__()

    async def _authenticate(self):
        return {}
