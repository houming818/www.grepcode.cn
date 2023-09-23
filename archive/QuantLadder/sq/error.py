
class SqRuntimeError(RuntimeError):
    def __init__(self, msg, *args, **kwargs):
        self.msg = msg

    def __str__(self):
        return self.msg


class SqParamError(RuntimeError):
    def __init__(self, msg, *args, **kwargs):
        self.msg = msg

    def __str__(self):
        return self.msg
