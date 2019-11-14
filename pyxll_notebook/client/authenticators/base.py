"""
Base implementation of Authenticators.
"""
import aiohttp


class Authenticator:

    def __init__(self):
        self.__cookie_jar = aiohttp.cookiejar.CookieJar()
        self.__headers = {}
        self.__authenticated = False

    async def _authenticate(self):
        """Implement in derived class.

        Should do any necessary authentication and return a dictionary of
        - headers
        - cookies
        """
        raise NotImplementedError()

    async def authenticate(self):
        """Do any necessary authentication and update headers and cookie_jar.
        """
        auth = await self._authenticate()
        headers = auth.get("headers")
        cookies = auth.get("cookies")
        if headers:
            self.__headers.update(headers)
        if cookies:
            self.__cookie_jar.update_cookies(cookies)
        self.__authenticated = True
        return auth

    @property
    def authenticated(self):
        """True if authenticate has been called at least once."""
        return self.__authenticated

    def reset(self):
        """Reset authenticator state"""
        self.__cookie_jar = aiohttp.cookiejar.CookieJar()
        self.__headers = {}
        self.__authenticated = False

    @property
    def headers(self):
        """List of extra headers to use in requests."""
        return self.__headers

    @property
    def cookie_jar(self):
        """Cookie jar to use for requests."""
        return self.__cookie_jar
