# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from ..checks import settings_checks


class CheckSessionCookieSecureTest(TestCase):
    @override_settings(AMAVIS_DEFAULT_DATABASE_ENCODING="LATIN-1")
    def test_amavis_database_encoding_incorrect(self):
        """
        If AMAVIS_DEFAULT_DATABASE_ENCODING is incorrect provide one warning.
        """
        self.assertEqual(
            settings_checks.check_amavis_database_encoding(None),
            [settings_checks.W001]
        )

    def test_amavis_database_encoding_correct(self):
        """
        If AMAVIS_DEFAULT_DATABASE_ENCODING is correct, there's no warning.
        """
        self.assertEqual(
            settings_checks.check_amavis_database_encoding(None),
            []
        )
