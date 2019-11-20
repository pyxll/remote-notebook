"""
Serialization for sending arguments and results between the client (Excel)
and server (IPyKernel).

Args and results are serialized to strings so that they can be used
in code snippets and passed around easily.
"""
import pickle
import base64

try:
    from ipykernel.kernelapp import IPKernelApp
except ImportError:
    IPKernelApp = None

_default_pickle_protocol = None


def _get_default_pickle_protocol():
    """Return the highest pickle prootocol supported by both server and client."""
    global _default_pickle_protocol
    if _default_pickle_protocol is not None:
        return _default_pickle_protocol

    app = IPKernelApp.instance() if IPKernelApp else None
    if app is None:
        _default_pickle_protocol = pickle.HIGHEST_PROTOCOL
        return _default_pickle_protocol

    user_ns = app.shell.user_ns
    pickle_protocol = user_ns.get("__pyxll_pickle_protocol__") or pickle.HIGHEST_PROTOCOL
    _default_pickle_protocol = min(pickle_protocol, pickle.HIGHEST_PROTOCOL)
    return _default_pickle_protocol


def serialize_args(args, protocol=None):
    """serialize a tuple of args to an escaped string"""
    if protocol is None:
        protocol = _get_default_pickle_protocol()
    data = pickle.dumps(args, protocol=protocol)
    encoded = base64.b64encode(data).decode()
    if not isinstance(encoded, str):
        encoded = str(encoded)
    return encoded


def deserialize_args(args):
    data = base64.b64decode(args)
    return pickle.loads(data)


def serialize_result(result, protocol=None):
    """serialize result from a Python function to send to the client"""
    if protocol is None:
        protocol = _get_default_pickle_protocol()
    data = pickle.dumps(result, protocol=protocol)
    encoded = base64.b64encode(data).decode()
    if not isinstance(encoded, str):
        encoded = str(encoded)
    return encoded


def deserialize_result(result):
    data = base64.b64decode(result)
    return pickle.loads(data)
