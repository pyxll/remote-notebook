"""
RTD equivalent for sending real time data to Excel from a remote notebook.
"""
from .session import get_session, send_message, register_server_function
from ..serialization import serialize_args, deserialize_args, serialize_result
from uuid import uuid4
import pickle

_active_rtd_instances = {}


@register_server_function("__pyxll_notebook_call_xl_rtd_method")
def _call_xl_rtd_method(id, method_name, args=None, protocol=pickle.HIGHEST_PROTOCOL):
    """Called from the client to invoke a method on an RTD instance"""
    rtd = _active_rtd_instances[id]

    # remove the RTD instance if disconnecting from Excel
    if method_name == "disconnect":
        del _active_rtd_instances[id]

    # call the method and return the result
    method = getattr(rtd, method_name)
    args = deserialize_args(args) if args else tuple()
    result = method(*args)
    return serialize_result(result, protocol=min(protocol, pickle.HIGHEST_PROTOCOL))


class RTD:
    """RTD is a base class that should be derived from for use by functions
    wishing to return real time ticking data instead of a static value.
    """
    def __init__(self, value=None):
        self.__id = str(uuid4())
        self.__value = value

    @property
    def id(self):
        return self.__id

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.set_value(value)

    def set_value(self, value):
        self.__value = value

        # send the update back to Excel
        session = get_session()
        if session:
            send_message(session, "xl_rtd_set_value", {
                "id": self.__id,
                "args": serialize_args((value,)),
            })

    def set_error(self, exc_type, exc_value, exc_traceback):
        # send the update back to Excel
        session = get_session()
        if session:
            send_message(session, "xl_rtd_set_error", {
                "id": self.__id,
                "args": serialize_args((exc_type, exc_value, exc_traceback)),
            })

    def connect(self):
        """Called when Excel connects to this RTD instance, which occurs shortly after
        an Excel function has returned an RTD object.
        May be overridden in the sub-class.
        """
        pass

    def disconnect(self):
        """Called when Excel no longer needs the RTD instance. This is usually because
        there are no longer any cells that need it or because Excel is shutting down.
        May be overridden in the sub-class.
        """
        pass

    @staticmethod
    def _create(id, value):
        rtd = RTD(value)
        rtd.__id = id
        return rtd

    def __reduce__(self):
        # When serialized to be sent to Excel, add to the set of active RTD instances.
        _active_rtd_instances[self.id] = self

        # There's no need to serialize the derived class, only the id and value are needed.
        return _create_rtd, (self.id, self.value)


def _create_rtd(id, value):
    return RTD._create(id, value)
