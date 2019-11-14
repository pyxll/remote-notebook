"""
Implementation of @xl_func wrapper to call the function in the remote kernel.

bind_xl_func is called from the Kernel handler in response to a "pyxll.xl_func"
message from the server.
"""
import pyxll
from ..serialization import serialize_args, deserialize_args, deserialize_result
from ..errors import ExecuteRequestError
from functools import wraps
from itertools import chain
import pickle
import asyncio


def bind_xl_func(kernel, func_name, **kwargs):
    """Creates a wrapper function for calling a remote @xl_func function."""
    xl_name = kwargs.get("name", func_name)
    args = kwargs.pop("args", None) or []
    varargs = kwargs.pop("varargs", None)
    pickle_protocol = min(kwargs.pop("pickle_protocol", pickle.HIGHEST_PROTOCOL), pickle.HIGHEST_PROTOCOL)
    defaults = kwargs.pop("defaults", None) or []
    if defaults:
        defaults = deserialize_args(defaults)

    # Build a function that looks like the one on the remote server
    args_without_defaults = [a for a in args[:len(args)-len(defaults)]]
    args_with_defaults = [f"{a}={a}" for a in args[len(args)-len(defaults):]]
    varargs = [f"*{varargs}"] if varargs else []

    doc = kwargs.pop("doc", None) or ""
    if doc:
        doc = '\n    """' + doc + '"""\n    '

    args_str = ", ".join(chain(args_without_defaults, args_with_defaults, varargs))
    func_str = f"def {func_name}({args_str}):{doc}pass"

    ns = {}
    if defaults:
        ns = {a: d for a, d in zip(reversed(args), reversed(defaults))}

    exec(func_str, {}, ns)
    dummy_func = ns[func_name]

    @wraps(dummy_func)
    def wrapper_function(*args):
        async def call_remote_function(args):
            args = serialize_args(args, protocol=pickle_protocol)
            expr = f"__pyxll_notebook_call_xl_func('{xl_name}', '{args}', protocol={pickle.HIGHEST_PROTOCOL})"
            reply = await kernel.execute('', user_expressions={"result": expr})

            result = reply["user_expressions"]["result"]
            status = result.get("status")
            if status != "ok":
                raise ExecuteRequestError(**result)

            data = result["data"]["text/plain"]
            return deserialize_result(data)

        loop = pyxll.get_event_loop()
        f = asyncio.run_coroutine_threadsafe(call_remote_function(args), loop)
        return f.result()

    wrapper_function.__name__ = func_name

    pyxll.xl_func(**kwargs)(wrapper_function)
    pyxll.rebind()
