import os
import json


class GlobalFlagUpdater:
    _instance = None
    _file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data_store.json"
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalFlagUpdater, cls).__new__(cls)
            cls._instance._data = {}
            cls._load_data()
        return cls._instance

    @classmethod
    def _load_data(cls):
        if os.path.exists(cls._file_path):
            with open(cls._file_path, "r") as file:
                cls._instance._data = json.load(file)

    @classmethod
    def save_data(cls):
        with open(cls._file_path, "w") as file:
            json.dump(cls._instance._data, file)

    def should_update(self, key):
        return self._data.get(key, False)

    def set_update_flag(self, key, value):
        self._data[key] = value
        self.save_data()
