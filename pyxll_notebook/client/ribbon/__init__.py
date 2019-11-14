"""
Ribbon functions for interacting with the Jupyter notebook server.
"""
from ..kernel_manager import KernelManager
import win32api
import win32con
import asyncio
import pyxll
import os

_icons = {
    "pyxll.notebooks.start_kernels": "start.png",
    "pyxll.notebooks.stop_kernels": "stop.png"
}

_ribbon = None
_notebooks = None
_selected_notebook = None


def on_load(control):
    global _ribbon
    _ribbon = control
    _init_notebooks()


def start_kernels(*args):
    """Starts the remote Jupyter kernels"""
    km = KernelManager.instance()
    loop = pyxll.get_event_loop()
    f = asyncio.run_coroutine_threadsafe(km.start_all_kernels(), loop)
    f.result()
    win32api.MessageBox(None, "Jupyter kernel started", "Jupyter kernel started", win32con.MB_ICONINFORMATION)


def stop_kernels(*args):
    """Starts the remote Jupyter kernels"""
    km = KernelManager.instance()
    loop = pyxll.get_event_loop()
    f = asyncio.run_coroutine_threadsafe(km.stop_all_kernels(), loop)
    f.result()
    win32api.MessageBox(None, "Jupyter kernel stopped", "Jupyter kernel stopped", win32con.MB_ICONINFORMATION)


def get_image(control):
    """Loads an image for the ribbon."""
    file = _icons.get(control.Id)
    if file:
        path = os.path.join(os.path.dirname(__file__), "icons", file)
        return pyxll.load_image(path)


def _init_notebooks():
    global _notebooks, _selected_notebook
    if _notebooks is None:
        cfg = pyxll.get_config()
        notebooks = cfg.get("NOTEBOOK", "notebooks", fallback="")
        _notebooks = [x for x in map(str.strip, notebooks.split(";")) if x]
        _notebooks.sort()


def notebook_current(control):
    return _selected_notebook


def notebook_count(control):
    return len(_notebooks)


def notebook_changed(notebook, control):
    global _selected_notebook
    _selected_notebook = notebook


def notebook_label(idx, control):
    return _notebooks[idx]


def refresh_notebooks(control):
    global _notebooks
    km = KernelManager.instance()
    loop = pyxll.get_event_loop()
    f = asyncio.run_coroutine_threadsafe(km.get_notebooks(), loop)
    notebooks = f.result()
    notebooks.sort()
    _notebooks = notebooks

    if _ribbon:
        _ribbon.InvalidateControl("pyxll.notebooks")


def run_notebook(control):
    if not _selected_notebook:
        raise AssertionError("No notebook selected")

    async def run():
        km = KernelManager.instance()
        kernel = await km.get_kernel(_selected_notebook)
        await kernel.run_notebook(_selected_notebook)

    loop = pyxll.get_event_loop()
    f = asyncio.run_coroutine_threadsafe(run(), loop)
    f.result()

    win32api.MessageBox(None, "Notebook run complete", "Notebook run complete", win32con.MB_ICONINFORMATION)
