class DictWrapper:
    """A wrapper around a dictionary to provide attribute-style access."""

    def __init__(self, data: dict = None):
        if data and not isinstance(data, dict):
            raise TypeError("DictWrapper can only wrap dictionaries")

        if not data:
            data = {}

        self._data = data

    @classmethod
    def _get_wrapper(cls, name: str = None):
        """
        Return the class of the wrapper object.
        Override this method in subclasses to provide a different wrapper if needed.
        """
        return DictWrapper

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getattr__(self, name: str = None):
        """Dynamically access dictionary keys as attributes."""

        # Check if the underlying _data dictionary has the attribute
        _data = self._get_data()

        if name in _data:
            value = _data[name]

            cls = self._get_wrapper(name)

            # Recursively wrap nested dictionaries
            if isinstance(value, dict):
                value = cls(value)

            # Recursively wrap lists containing dictionaries
            if isinstance(value, list):
                value = [cls(item) if isinstance(item, dict) else item for item in value]

            _data[name] = value  # Update the dictionary with the wrapped value

            return value

        # Delegate method calls to the underlying dictionary
        if hasattr(_data, name) and callable(getattr(_data, name)):
            return getattr(_data, name)

        # raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        raise AttributeError(f"name: {name}")

    def __getitem__(self, key):
        """Allow dictionary-style access."""
        return self._data[key]

    def __repr__(self):
        """Provide a string representation of the wrapped dictionary."""
        return f"{type(self).__name__}({self._data})"

    def _get_data(self):
        """Return the wrapped dictionary."""
        return self._data or {}

    def to_dict(self):
        """Return the original dictionary."""
        return self._data
    
    def get(self, key, default=None):
        """Get the value for a key, returning default if not found."""
        _data = self._get_data()
        val = _data.get(key, default)
        return val
