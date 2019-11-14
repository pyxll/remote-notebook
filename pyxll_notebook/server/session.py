from ipykernel.kernelapp import IPKernelApp

_session = None


def get_session():
    """Return the session id of the owner PyXLL client, or None."""
    global _session
    if _session is not None:
        return _session

    app = IPKernelApp.instance()
    if app is None:
        return None

    user_ns = app.shell.user_ns
    _session = user_ns.get("__pyxll_notebook_session__")
    return _session


def send_message(msg_type, content):
    """Sends a message back to the client."""
    app = IPKernelApp.instance()
    if app is None:
        raise AssertionError("No IPKernelApp found.")

    session = get_session()
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
