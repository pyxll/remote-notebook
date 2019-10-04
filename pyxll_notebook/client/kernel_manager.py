"""
KernelManager class for starting and stopping the remote
kernels for each notebook in the configuration.
"""
from pyxll import get_config
from .kernel import Kernel
from . import authenticators
import asyncio


class KernelManager:
    _instance = None

    def __init__(self):
        self.__kernels = []

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start_all_kernels(self):
        """Start or restart the remote kernels"""
        await asyncio.sleep(0)  # make sure we're on the asyncio thread

        # stop any running kernel
        await self.stop_all_kernels()

        cfg = get_config()
        url = cfg.get("NOTEBOOK", "url", fallback="https://localhost:8888")
        notebooks = cfg.get("NOTEBOOK", "notebooks", fallback="")
        notebooks = [x for x in map(str.strip, notebooks.split(";")) if x]

        # get the authenticator
        auth = None
        auth_class = cfg.get("NOTEBOOK", "auth_class")
        if auth_class:
            cls = getattr(authenticators, auth_class, None)
            if cls is None:
                package, cls_name = auth_class.rsplit(".", 1)
                module = __import__(package, fromlist=[cls_name])
                cls = getattr(module, cls_name, None)
            if cls is None:
                raise AssertionError(f"Authentication class '{auth_class}' not found.")

            kwargs = dict(cfg["NOTEBOOK"])
            kwargs["url"] = url
            kwargs["notebooks"] = notebooks
            auth = cls(**kwargs)

        for notebook in notebooks:
            kernel = Kernel(url, authenticator=auth)
            self.__kernels.append(kernel)
            await kernel.start()
            await kernel.run_notebook(notebook)

    async def stop_all_kernels(self):
        """Shutdown the remotes kernel"""
        await asyncio.sleep(0)  # make sure we're on the asyncio thread

        tasks = []
        while self.__kernels:
            kernel = self.__kernels.pop(0)
            tasks.append(kernel.shutdown())
        await asyncio.gather(*tasks)
