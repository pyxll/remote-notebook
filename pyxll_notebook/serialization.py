"""
Serialization for sending arguments and results between the client (Excel)
and server (IPyKernel).

Args and results are serialized to strings so that they can be used
in code snippets and passed around easily.
"""
import pickle
import base64


def serialize_args(args, protocol=pickle.HIGHEST_PROTOCOL):
    """serialize a tuple of args to an escaped string"""
    data = pickle.dumps(args, protocol=protocol)
    encoded = base64.b64encode(data).decode()
    if not isinstance(encoded, str):
        encoded = str(encoded)
    return encoded


def deserialize_args(args):
    data = base64.b64decode(args)
    return pickle.loads(data)


def serialize_result(result, protocol=pickle.HIGHEST_PROTOCOL):
    """serialize result from a Python function to send to the client"""
    data = pickle.dumps(result, protocol=protocol)
    encoded = base64.b64encode(data).decode()
    if not isinstance(encoded, str):
        encoded = str(encoded)
    return encoded


def deserialize_result(result):
    data = base64.b64decode(result)
    return pickle.loads(data)
