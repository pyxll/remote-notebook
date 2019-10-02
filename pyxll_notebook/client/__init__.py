"""
The pyxll_notebook.client package contains everything needed for the Excel/PyXLL
client to talk to the notebook server.

It should be included in the pyxll.cfg list of modules, and configured
in the [NOTEBOOK] section of the config.
"""
from pyxll import get_event_loop, xl_on_open, xl_on_reload, xl_on_close, xl_menu
from .kernel import Kernel
from .handler import Handler
from pyxll_notebook.errors import KernelStartError, ExecuteRequestError
from .kernel_manager import KernelManager
import asyncio


__all__ = [
    "Kernel",
    "Handler",
    "KernelStartError",
    "ExecuteRequestError",
    "KernelManager"
]


@xl_on_open
@xl_on_reload
def on_open(import_info):
    """Start the remote kernel when Excel starts up, or PyXLL is reloaded.
    """
    km = KernelManager.instance()
    loop = get_event_loop()
    f = asyncio.run_coroutine_threadsafe(km.start_all_kernels(), loop)
    f.result()


@xl_on_close
def on_close():
    """Shuts down any running kernels.

    Note: This is called when the user 'closes' Excel, but before the confirm
    prompt is shown so if they cancel then the kernel will no longer be running.
    """
    km = KernelManager.instance()
    loop = get_event_loop()
    f = asyncio.run_coroutine_threadsafe(km.stop_all_kernels(), loop)
    f.result()
