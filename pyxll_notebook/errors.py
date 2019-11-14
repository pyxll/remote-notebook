"""
Exceptions thrown by pyxll_notebook.
"""


class KernelStartError(RuntimeError):
    pass


class ExecuteRequestError(RuntimeError):
    def __init__(self, evalue=None, traceback=None, **kwargs):
        if evalue is None:
            evalue = str(kwargs)
        super().__init__(evalue)


class AuthenticationError(RuntimeError):
    pass
