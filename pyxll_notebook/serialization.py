"""
Serialization for sending arguments and results between the client (Excel)
and server (IPyKernel).

Args and results are serialized to strings so that they can be used
in code snippets and passed around easily.
"""
import pickle
import base64


def serialize_args(args):
    """serialize a tuple of args to an escaped string"""
    data = pickle.dumps(args)
    return base64.b64encode(data).decode()


def deserialize_args(args):
    data = base64.b64decode(args)
    return pickle.loads(data)


def serialize_result(result):
    """serialize result from a Python function to send to the client"""
    data = pickle.dumps(result)
    return base64.b64encode(data).decode()


def deserialize_result(result):
    data = base64.b64decode(result)
    return pickle.loads(data)
