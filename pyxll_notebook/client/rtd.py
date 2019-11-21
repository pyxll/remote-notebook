"""
Implementation of RTD class to receive updates from the remote RTD instance.
"""
from ..errors import ExecuteRequestError
import pyxll
import pickle

_active_rtd_instances = {}


class RTD(pyxll.RTD):

    def __init__(self, kernel, id, value, pickle_protocol=pickle.HIGHEST_PROTOCOL):
        super().__init__(value=value)
        self.__kernel = kernel
        self.__id = id
        self.__pickle_protocol = min(pickle_protocol, pickle.HIGHEST_PROTOCOL)
        _active_rtd_instances[self.__id] = self

    async def connect(self):
        expr = f"__pyxll_notebook_call_xl_rtd_method('{self.__id}', 'connect')"
        reply = await self.__kernel.execute('', user_expressions={"result": expr})

        result = reply["user_expressions"]["result"]
        status = result.get("status")
        if status != "ok":
            raise ExecuteRequestError(**result)

    async def disconnect(self):
        try:
            del _active_rtd_instances[self.__id]
        except KeyError:
            pass

        expr = f"__pyxll_notebook_call_xl_rtd_method('{self.__id}', 'disconnect')"
        reply = await self.__kernel.execute('', user_expressions={"result": expr})

        result = reply["user_expressions"]["result"]
        status = result.get("status")
        if status != "ok":
            raise ExecuteRequestError(**result)


def create_client_rtd(kernel, server_rtd, pickle_protocol=pickle.HIGHEST_PROTOCOL):
    """Return an client-side RTD instance from a server side RTD object."""
    return RTD(kernel, server_rtd.id, server_rtd.value, pickle_protocol=pickle_protocol)


def xl_rtd_set_value(id, value):
    rtd = _active_rtd_instances.get(id)
    if rtd is not None:
        rtd.value = value


def xl_rtd_set_error(id, *args, **kwargs):
    rtd = _active_rtd_instances.get(id)
    if rtd is not None:
        rtd.set_error(*args, **kwargs)
