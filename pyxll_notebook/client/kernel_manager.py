"""
KernelManager class for starting and stopping the remote
kernels for each notebook in the configuration.
"""
from pyxll import get_config
from .kernel import Kernel
from . import authenticators
import asyncio
import aiohttp


class KernelManager:
    _instance = None

    def __init__(self, cfg):
        notebooks = cfg.get("NOTEBOOK", "notebooks", fallback="")
        self.__notebooks = [x for x in map(str.strip, notebooks.split(";")) if x]
        self.__url = cfg.get("NOTEBOOK", "url", fallback="https://localhost:8888")
        self.__auth_class = cfg.get("NOTEBOOK", "auth_class", fallback="NoAuthAuthenticator")
        self.__cfg = cfg
        self.__authenticator = None
        self.__kernels = {}

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cfg = get_config()
            cls._instance = cls(cfg)
        return cls._instance

    @property
    def is_running(self):
        """Returns true if there are any kernels running."""
        return bool(self.__kernels)

    def __get_authenticator(self):
        """Return the authenticator for connecting to the notebook server."""
        if self.__authenticator:
            return self.__authenticator

        if self.__auth_class:
            cls = getattr(authenticators, self.__auth_class, None)
            if cls is None:
                package, cls_name = self.__auth_class.rsplit(".", 1)
                module = __import__(package, fromlist=[cls_name])
                cls = getattr(module, cls_name, None)
            if cls is None:
                raise AssertionError(f"Authentication class '{self.__auth_class}' not found.")

            kwargs = dict(self.__cfg["NOTEBOOK"])
            kwargs["url"] = self.__url
            kwargs["notebooks"] = self.__notebooks
            self.__authenticator = cls(**kwargs)

        return self.__authenticator

    async def start_all_kernels(self):
        """Start or restart the remote kernels"""
        await asyncio.sleep(0)  # make sure we're on the asyncio thread

        # stop any running kernel
        await self.stop_all_kernels()

        # run any notebooks listed in the config
        for notebook in self.__notebooks:
            kernel = await self.get_kernel(notebook)
            await kernel.run_notebook(notebook)

    async def get_kernel(self, notebook):
        """Get a kernel for a notebook, and start one if it doesn't already exist"""
        kernel = self.__kernels.get(notebook)
        if kernel:
            return kernel

        auth = self.__get_authenticator()
        kernel = Kernel(self.__url, authenticator=auth)
        await kernel.start()
        self.__kernels[notebook] = kernel
        return kernel

    async def get_notebooks(self):
        """Return a list of available notebooks from the notebook server"""
        auth = self.__get_authenticator()
        if not auth.authenticated:
            await auth.authenticate()

        url = self.__url + "/api/contents"
        async with aiohttp.ClientSession(cookie_jar=auth.cookie_jar) as session:
            async with session.get(url, headers=auth.headers) as response:
                try:
                    await response.read()
                    response.raise_for_status()
                    contents = await response.json()
                except Exception:
                    auth.reset()
                    raise

                return [x["path"] for x in contents["content"] if x.get("type") == "notebook"]

    async def stop_all_kernels(self):
        """Shutdown the remotes kernel"""
        await asyncio.sleep(0)  # make sure we're on the asyncio thread

        tasks = []
        while self.__kernels:
            notebook, kernel = self.__kernels.popitem()
            tasks.append(kernel.shutdown())
        await asyncio.gather(*tasks)
