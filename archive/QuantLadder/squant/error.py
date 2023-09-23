
class SquantParamError(KeyError):
    def __init__(self, msg, *args, **kwargs):
        self.msg = msg

    def __str__(self):
        return self.msg


class SquantRuntimeError(RuntimeError):
    def __init__(self, msg, *args, **kwargs):
        self.msg = msg

    def __str__(self):
        return self.msg


class SquantConfigError(RuntimeError):
    def __init__(self, msg, *args, **kwargs):
        self.msg = msg

    def __str__(self):
        return self.msg

class SquantSdkError(RuntimeError):
    def __init__(self, msg, *args, **kwargs):
        self.msg = msg

    def __str__(self):
        return self.msg
