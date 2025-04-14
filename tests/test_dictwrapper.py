import pytest
from vsbuildkit.utils.dictwrapper import DictWrapper


class TestDictWrapper:
    def test_initialization(self):
        # Test initialization with a dictionary
        data = {"key": "value"}
        wrapper = DictWrapper(data)
        assert wrapper._data == data

        # Test initialization with None
        wrapper = DictWrapper()
        assert wrapper._data == {}

        # Test initialization with invalid type
        with pytest.raises(TypeError):
            DictWrapper("not a dict")

    def test_len(self):
        data = {"key1": "value1", "key2": "value2"}
        wrapper = DictWrapper(data)
        assert len(wrapper) == 2

    def test_iter(self):
        data = {"key1": "value1", "key2": "value2"}
        wrapper = DictWrapper(data)
        keys = list(iter(wrapper))
        assert keys == ["key1", "key2"]

    def test_getattr(self):
        data = {"key": "value", "nested": {"inner_key": "inner_value"}}
        wrapper = DictWrapper(data)

        # Access existing key as attribute
        assert wrapper.key == "value"

        # Access nested dictionary as attribute
        nested = wrapper.nested
        assert isinstance(nested, DictWrapper)
        assert nested.inner_key == "inner_value"

        # Access non-existent key
        with pytest.raises(AttributeError):
            _ = wrapper.non_existent_key

    def test_getitem(self):
        # Test accessing an existing key
        data = {"key1": "value1", "key2": "value2"}
        wrapper = DictWrapper(data)

        assert wrapper["key1"] == "value1"
        assert wrapper["key2"] == "value2"

        # Test accessing a non-existent key
        with pytest.raises(KeyError, match="non_existent_key"):
            _ = wrapper["non_existent_key"]

    def test_repr(self):
        data = {"key": "value"}
        wrapper = DictWrapper(data)
        assert repr(wrapper) == "DictWrapper({'key': 'value'})"

    def test_to_dict(self):
        data = {"key": "value"}
        wrapper = DictWrapper(data)
        assert wrapper.to_dict() == data

    def test_get_data(self):
        wrapper = DictWrapper()
        assert wrapper._get_data() == {}

        wrapper = DictWrapper({"key": "value"})
        assert wrapper._get_data() == {"key": "value"}

    def test_nested_list_wrapping(self):
        data = {"key": [{"nested_key": "nested_value"}]}
        wrapper = DictWrapper(data)

        # Access nested list containing dictionaries
        nested_list = wrapper.key
        assert isinstance(nested_list, list)
        assert isinstance(nested_list[0], DictWrapper)
        assert nested_list[0].nested_key == "nested_value"

    def test_delegate_method_calls(self):
        data = {"key": "value"}
        wrapper = DictWrapper(data)

        # Test dictionary method delegation
        assert wrapper.get("key") == "value"
        assert wrapper.get("non_existent_key") is None