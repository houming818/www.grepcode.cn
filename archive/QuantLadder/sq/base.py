
from .data import Dao

class SqContext(object):
    initilized = False
    pockets = {}
    cache = {}

    def __init__(self):
        self._Dao = Dao(self)
        self._config = {}

    def init(
        self,
        influxdb_settings,
        *args,
        **kwargs
    ):
        if influxdb_settings is None:
            raise SqRuntimeError("influx_settings is required")
        self.config['influxdb_settings'] =  influxdb_settings
        self.initilized = True

    def __getattribute__(self, key):
        if key == 'config':
            return self._config
        elif key == 'Dao':
            return self._Dao
        else:
            # Default behaviour
            return object.__getattribute__(self, key)

    def __getitem__(self, key):
        if self.initilized == False:
            raise SqRuntimeError('SqContext not initilized')
        return self.pockets.get(key, None)

    def __setitem__(self, key, value):
        if self.initilized == False:
            raise SqRuntimeError('SqContext not initilized')
        self.pockets[key] = value

