# -*- coding: utf-8 -*-

"""The amavis frontend of Modoboa."""

from __future__ import unicode_literals

import collections

from pkg_resources import DistributionNotFound, get_distribution

import django.test.utils as utils
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import dependency_ordered

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:  # pragma: no cover
    # package is not installed
    pass

default_app_config = "modoboa_amavis.apps.AmavisConfig"


# a modified version of django.test.utils.get_unique_databases_and_mirrors used
# to skip the creation of the Amavis database.
def _get_unique_databases_and_mirrors():
    """
    Figure out which databases actually need to be created.
    Deduplicate entries in DATABASES that correspond the same database or are
    configured as test mirrors.
    Return two values:
    - test_databases: ordered mapping of signatures to (name, list of aliases)
                      where all aliases share the same underlying database.
    - mirrored_aliases: mapping of mirror aliases to original aliases.

    See https://github.com/django/django/blob/1.11.10/django/test/utils.py#L254
    """
    mirrored_aliases = {}
    test_databases = {}
    dependencies = {}
    default_sig = connections[DEFAULT_DB_ALIAS].creation.test_db_signature()

    for alias in connections:
        if alias == "amavis":
            # Don't create the Amavis database, that's managed externaly.
            continue

        connection = connections[alias]
        test_settings = connection.settings_dict['TEST']

        if test_settings['MIRROR']:
            # If the database is marked as a test mirror, save the alias.
            mirrored_aliases[alias] = test_settings['MIRROR']
        else:
            # Store a tuple with DB parameters that uniquely identify it.
            # If we have two aliases with the same values for that tuple,
            # we only need to create the test database once.
            item = test_databases.setdefault(
                connection.creation.test_db_signature(),
                (connection.settings_dict['NAME'], set())
            )
            item[1].add(alias)

            if 'DEPENDENCIES' in test_settings:
                dependencies[alias] = test_settings['DEPENDENCIES']
            else:
                if (
                    alias != DEFAULT_DB_ALIAS and
                    connection.creation.test_db_signature() != default_sig
                ):
                    dependencies[alias] = test_settings.get(
                        'DEPENDENCIES', [DEFAULT_DB_ALIAS]
                    )

    test_databases = dependency_ordered(
        test_databases.items(), dependencies
    )
    test_databases = collections.OrderedDict(test_databases)
    return test_databases, mirrored_aliases


# monkey patch the modified version of get_unique_databases_and_mirrors()
utils.get_unique_databases_and_mirrors = _get_unique_databases_and_mirrors
