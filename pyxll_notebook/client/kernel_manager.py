"""
KernelManager class for starting and stopping the remote
kernels for each notebook in the configuration.
"""
from pyxll import get_config
from .kernel import Kernel
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
        host = cfg.get("NOTEBOOK", "server", fallback="https://localhost:8888")

        protocol = "http"
        port = None
        path = None
        if "://" in host:
            idx = host.find("://")
            protocol, host = host[:idx], host[idx+3:]

        if "/" in host:
            host, path = host.split("/", 1)

        if ":" in host:
            host, port = host.split(":", 1)
            port = int(port)

        auth_token = cfg.get("NOTEBOOK", "auth_token", fallback=None)
        notebooks = cfg.get("NOTEBOOK", "notebooks", fallback="")
        notebooks = [x for x in map(str.strip, notebooks.split(";")) if x]

        # load each notebook in a new kernel
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Token {auth_token}"

        for notebook in notebooks:
            kernel = Kernel(host, protocol=protocol, port=port, path=path, headers=headers)
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
