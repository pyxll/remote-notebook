try:
    from ipykernel.kernelapp import IPKernelApp
except ImportError:
    IPKernelApp = None

_session = None


def get_session():
    """Return the session id of the owner PyXLL client, or None."""
    global _session
    if _session is not None:
        return _session

    app = IPKernelApp.instance() if IPKernelApp else None
    if app is None:
        return None

    user_ns = app.shell.user_ns
    _session = user_ns.get("__pyxll_notebook_session__")
    return _session


def send_message(session, msg_type, content):
    """Sends a message back to the client."""
    app = IPKernelApp.instance() if IPKernelApp else None
    if app is None:
        raise AssertionError("No IPKernelApp found.")

    if session is None:
        raise AssertionError("No PyXLL client session found.")

    parent = {
        "header": {
            "session": session
        }
    }

    app.session.send(app.iopub_socket,
                     msg_type,
                     content=content,
                     parent=parent)


def register_server_function(name):
    """Registers a function that can be called from the client"""
    def make_decorator(name):
        def decorator(func):
            app = IPKernelApp.instance() if IPKernelApp else None
            if app and app.shell:
                app.shell.user_ns.setdefault(name, func)
        return decorator
    return make_decorator(name)
