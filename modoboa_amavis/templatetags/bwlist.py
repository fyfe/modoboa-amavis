# -*- coding: utf-8 -*-

"""Django template tags used by black/white listing views."""

from __future__ import unicode_literals

from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _


register = template.Library()


def bwl_action_desc(value, hard_bw_mode):
    """Display the correct action description dpending on hard_bw_mode."""
    description = ""
    if hard_bw_mode:
        if value == "W":
            description = _("e-mails matching this entry will bypass spam "
                            "checks and will always be accepted.")
        elif value == "B":
            description = _("e-mails matching this entry will bypass spam "
                            "checks and will always be rejected.")
        else:
            description = _("e-mails matching this entry will be treated as "
                            "neutral and spaminess will be determined using "
                            "normal spam checks.")
    else:
        description = _("e-mails matching this entry will have %.3f added to "
                        "their SpamAssassin score.") % value

    return description


def bwl_action_value(value, hard_bw_mode):
    """Format action value dpending on hard_bw_mode."""
    display_value = ""
    if hard_bw_mode:
        if value == "W":
            display_value = mark_safe(
                "<span class=\"glyphicon glyphicon-ok\"></span>"
                "<span class=\"sr-only\">%s</span>" % _("white list")
            )
        elif value == "B":
            display_value = mark_safe(
                "<span class=\"glyphicon glyphicon-remove\"></span>"
                "<span class=\"sr-only\">%s</span>" % _("black list")
            )
        else:
            display_value = mark_safe(
                "<span class=\"glyphicon glyphicon-minus\"></span>"
                "<span class=\"sr-only\">%s</span>" % _("neutral")
            )
    else:
        display_value = "%.3f" % value

    return display_value
