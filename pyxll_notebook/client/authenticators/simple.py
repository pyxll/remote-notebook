"""Simple authenticator that takes the token
from the config.
"""
import pyxll


class SimpleAuthenticator:

    def __init__(self, auth_token=None, **kwargs):
        if not auth_token:
                raise Exception("Set 'auth_token' in the NOTEBOOK section of the config.")
        self.__auth_token = auth_token

    async def authenticate(self):
        return {
            "headers": {
                "Authorization":  f"Token {self.__auth_token}"
            }
        }

