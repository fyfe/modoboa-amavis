# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.views import generic

from modoboa.parameters import tools as param_tools

from modoboa_amavis.lib import make_query_args
from modoboa_amavis.models import policy as policy_models
from modoboa_amavis.utils import ConvertFrom


class BlackWhiteListView(UserPassesTestMixin, generic.ListView):

    """Display a list of the users black/white listed e-mail addresses.

    This view can be filtered by recipient to see a listing for a specific
    mailbox/aliases belonging to the user."""

    model = policy_models.BlackWhiteList
    ordering = ["-recipient__priority", "-sender__priority"]

    def __init__(self, *args, **kwargs):
        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
        self.hard_bw_mode = bool(conf["hard_wb_mode"] or False)
        super(BlackWhiteListView, self).__init__(*args, **kwargs)

    def get_queryset(self):
        queryset = super(BlackWhiteListView, self).get_queryset()
        rcpts = [self.user.email]
        if hasattr(self.user, "mailbox"):
            rcpts += self.user.mailbox.alias_addresses

        if "recipient" in self.kwargs and self.kwargs["recipient"]:
            if self.kwargs["recipient"] in rcpts:
                filter_query = Q(
                    str_rcpt_email__iexact=self.kwargs["recipient"]
                )
            else:
                return queryset.none()
        else:
            query_rcpts = []
            for rcpt in rcpts:
                query_rcpts += make_query_args(
                    rcpt, exact_extension=False, wildcard=".*",
                    domain_search=True
                )

            re = "(%s)" % "|".join(query_rcpts)
            filter_query = Q(str_rcpt_email__regex=re)

        return (
            queryset
            .annotate(str_rcpt_email=ConvertFrom("recipient__email"))
            .filter(filter_query)
            .all()
        )

    def test_func(self):
        """The user requires a mailbox to use black/white listing."""
        return hasattr(self.user, "mailbox")
