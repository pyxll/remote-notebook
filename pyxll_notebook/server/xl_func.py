"""
@xl_func decorator equivalent for registering remote notebook functions.
"""
from .session import get_session, send_message
from ..serialization import serialize_args, deserialize_args, serialize_result
from ipykernel.kernelapp import IPKernelApp
import inspect


_registered_xl_funcs = {}


def _call_xl_func(func_name, args):
    """Called from the client to invoke a registered xl_func"""
    func = _registered_xl_funcs[func_name]
    args = deserialize_args(args)
    result = func(*args)
    return serialize_result(result)


def xl_func(signature=None,
            category="PyXLL",
            help_topic="",
            thread_safe=False,
            macro=False,
            allow_abort=None,
            volatile=None,
            disable_function_wizard_calc=False,
            disable_replace_calc=False,
            name=None,
            auto_resize=False,
            hidden=False):
    """
    xl_func is decorator used to expose python functions to Excel.

    Functions exposed in this way can be called from formulas in an Excel worksheet and
    appear in the Excel function wizard.

    See pyxll.xl_func for full details.
    """
    # xl_func may be called with no arguments as a plain decorator, in which
    # case the first argument will be the function it's applied to.
    func = None
    if signature is not None and callable(signature):
        func = signature
        signature = None

    def xl_func_decorator(func):
        xl_name = name or func.__name__
        session = get_session()
        if session:
            # Add __pyxll_notebook_call_xl_func to user_ns
            app = IPKernelApp.instance()
            app.shell.user_ns.setdefault("__pyxll_notebook_call_xl_func", _call_xl_func)

            # func will be called via _call_xl_func from the client
            _registered_xl_funcs[xl_name] = func

            # register the function on the client
            getargspec = inspect.getfullargspec if hasattr(inspect, "getfullargspec") else inspect.getargspec
            spec = getargspec(func)
            msg = {
                "func": func.__name__,
                "args": spec.args,
                "varargs": spec.varargs,
                "defaults": serialize_args(spec.defaults) if spec.defaults else None,
                "doc": func.__doc__,
                "signature": signature,
                "category": category,
                "help_topic": help_topic,
                "thread_safe": thread_safe,
                "macro": macro,
                "allow_abort": allow_abort,
                "volatile": volatile,
                "disable_function_wizard_calc": disable_function_wizard_calc,
                "disable_replace_calc": disable_replace_calc,
                "name": xl_name,
                "auto_resize": auto_resize,
                "hidden": hidden
            }
            send_message("xl_func", msg)

        return func

    if func is not None:
        return xl_func_decorator(func)

    return xl_func_decorator
