from tele_bridge.bases.client_params import ClientOpts
from tele_bridge.bases.mixins import SetAttribute


class BaseClient(SetAttribute):
    def __init__(self, opts: ClientOpts = None):
        if hasattr(self, '_initialized') and self._initialized:
            return  # Если уже инициализирован, просто возвращаем

        # Если инициализация не была проведена, выполняем её
        self._attribute_cache = {}
        self._set_attr_timeout = opts.set_attr_timeout
        self.phone_number_error = opts.phone_number_error
        self.phone_code_error = opts.phone_code_error
        self.password_error = opts.password_error

        self._initialized = True  # Устанавливаем флаг для текущего экземпляра