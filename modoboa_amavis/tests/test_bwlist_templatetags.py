# -*- coding: utf-8 -*-

"""Tests for black/white listing template tags."""

from __future__ import unicode_literals

from django.test import SimpleTestCase

from modoboa_amavis.models.policy import BlackWhiteList
from modoboa_amavis.templatetags.bwlist import bwl_action_value


class BWListTemplateTagsTest(SimpleTestCase):

    """Tests for black/white listing template tags."""

    def test_bwl_action_value_hard_mode(self):
        """bwl_action_value() in hard mode."""
        for value in ["W", "B", None]:
            output = bwl_action_value(value, True)
            expected_output_contains = "glyphicon"
            self.assertContains(output, expected_output_contains)

    def test_bwl_action_value_soft_mode(self):
        """bwl_action_value() in soft mode."""
        value = BlackWhiteList._SCORE_DECIMAL_CONTEXT.create_decimal(2.54)
        output = bwl_action_value(value, True)
        expected_output = "%.3f" % value
        self.assertEqual(output, expected_output)
