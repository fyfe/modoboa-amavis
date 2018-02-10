# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import models
from django.utils import six
from django.utils.datastructures import DictWrapper
from django.utils.encoding import force_bytes, force_text


class BinaryCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        super(BinaryCharField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "BinaryCharField"

    def db_type(self, connection):  # ✓
        data = DictWrapper(self.__dict__, connection.ops.quote_name, "qn_")
        try:
            return connection.data_types["BinaryField"] % data
        except KeyError:
            return None

    def rel_db_type(self, connection):  # ✓
        return self.db_type(connection)

    def value_to_string(self, obj):
        if isinstance(obj, memoryview):
            print(
                "BinaryCharField", "value_to_string",
                type(obj), six.text_type(obj)
            )
        return self._to_string(obj)

    def to_python(self, value):
        if isinstance(value, memoryview):
            print(
                "BinaryCharField", "to_python",
                type(value), six.text_type(value)
            )
        return self._to_string(value)

    def from_db_value(self, value, expression, connection, context):  # ✓
        return self._to_string(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, memoryview):
            print(
                "BinaryCharField", "get_db_prep_value",
                type(value), six.text_type(value)
            )
        value = super(BinaryCharField, self).get_db_prep_value(
            value, connection, prepared
        )
        if value is not None:
            return self._to_bytes(value)
        return value

    def get_prep_value(self, value):
        if isinstance(value, memoryview):
            print(
                "BinaryCharField", "get_prep_value",
                type(value), six.text_type(value)
            )
        return self._to_bytes(value)

    @staticmethod
    def _to_string(value):
        if value is None:
            return None
        if isinstance(value, memoryview):
            # psycopg2 returms bytea fields as memoryview.
            # Django force_text() always returns an instance of memoryview.
            return value.tobytes().decode("utf8")
        return force_text(value)

    @staticmethod
    def _to_bytes(value):
        if value is None:
            return None
        if isinstance(value, memoryview):
            # psycopg2 returms bytea fields as memoryview.
            # Django force_bytes() trys bytes(value) which doesn't work on PY2
            # it still returns an instance of memoryview, use
            # memoryview.tobytes() instead.
            return value.tobytes()
        return force_bytes(value)


class BinaryForeignKey(models.ForeignKey):
    def __init__(self, *args, **kwargs):
        super(BinaryForeignKey, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "BinaryForeignKey"

    def db_type(self, connection):  # ✓
        data = DictWrapper(self.__dict__, connection.ops.quote_name, "qn_")
        try:
            return connection.data_types["BinaryField"] % data
        except KeyError:
            return None

    def rel_db_type(self, connection):  # ✓
        return self.db_type(connection)

    def value_to_string(self, obj):
        if isinstance(obj, memoryview):
            print(
                "BinaryForeignKey", "value_to_string",
                type(obj), six.text_type(obj)
            )
        return self._to_string(obj)

    def to_python(self, value):
        if isinstance(value, memoryview):
            print(
                "BinaryForeignKey", "to_python",
                type(value), six.text_type(value)
            )
        return self._to_string(value)

    def from_db_value(self, value, expression, connection, context):
        if isinstance(value, memoryview):
            print(
                "BinaryForeignKey", "value_to_string",
                type(value), six.text_type(value)
            )
        return self._to_string(value)

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, memoryview):
            print(
                "BinaryForeignKey", "get_db_prep_value",
                type(value), six.text_type(value)
            )
        value = super(BinaryForeignKey, self).get_db_prep_value(
            value, connection, prepared
        )
        if value is not None:
            return self._to_bytes(value)
        return value

    def get_prep_value(self, value):
        if isinstance(value, memoryview):
            print(
                "BinaryForeignKey", "get_prep_value",
                type(value), six.text_type(value)
            )
        return self._to_bytes(value)

    @staticmethod
    def _to_string(value):
        if value is None:
            return None
        if isinstance(value, memoryview):
            # psycopg2 returms bytea fields as memoryview.
            # Django force_text() always returns an instance of memoryview.
            return value.tobytes().decode("utf8")
        return force_text(value)

    @staticmethod
    def _to_bytes(value):
        if value is None:
            return None
        if isinstance(value, memoryview):
            # psycopg2 returms bytea fields as memoryview.
            # Django force_bytes() trys bytes(value) which doesn't work on PY2
            # it still returns an instance of memoryview, use
            # memoryview.tobytes() instead.
            return value.tobytes()
        return force_bytes(value)
