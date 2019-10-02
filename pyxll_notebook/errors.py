"""
Exceptions thrown by pyxll_notebook.
"""


class KernelStartError(RuntimeError):
    pass


class ExecuteRequestError(RuntimeError):
    def __init__(self, evalue, **kwargs):
        super().__init__(evalue)
