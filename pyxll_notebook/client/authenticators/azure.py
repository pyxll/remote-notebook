"""Authenticator class for connecting to Azure notebooks
"""
from .browser_auth import BrowserAuthenticator


class AzureAuthenticator(BrowserAuthenticator):

    notebooks_url = "https://notebooks.azure.com"

    def __init__(self, notebooks, azure_user_id=None, azure_project=None, **kwargs):
        super().__init__(**kwargs)
        if not azure_user_id or not azure_project:
            raise AssertionError("azure_user_id and azure_project must be specified.")
        self.__login_clicked = False
        self.__notebooks = notebooks
        self.__user_id = azure_user_id
        self.__project = azure_project

    def _extra_kwargs(self):
        """extra kwargs to use to create a clone not used by the base class."""
        return {
            "notebooks": self.__notebooks,
            "azure_user_id": self.__user_id,
            "azure_project": self.__project
        }

    @property
    def _login_url(self):
        """Return the URL for one of the configured notebooks.
        This is to login and get the auth token, so any notebook will do.
        """
        notebook = self.__notebooks[0]
        return f"{self.notebooks_url}/{self.__user_id}/projects/{self.__project}/run/notebooks/{notebook}"

    def _on_page_loaded(self, browser, *args):
        """Run some Javascript to look for the sign in button and click it."""
        if not self.__login_clicked:
            def callback(clicked):
                self.__login_clicked = clicked

            browser.runJavaScript("""
                var login = document.querySelector("a[href='/account/signin#']");
                var clicked = 0;
                if (login) {
                    login.click();
                    clicked = 1;
                }
                clicked;
            """, callback)
