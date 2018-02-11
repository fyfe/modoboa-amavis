# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db.models import Q

from rest_framework import permissions

from modoboa.admin.models import Domain
from modoboa_amavis.lib import manual_learning_enabled
from modoboa_amavis.models import Msgrcpt
from modoboa_amavis.sql_connector import make_query_args
from modoboa_amavis.utils import ConvertFrom


class AllowedQuarantineAccess(permissions.BasePermission):

    def has_permission(self, request, view):
        if view.action in ["mark_as_spam", "mark_as_ham"]:
            return manual_learning_enabled(request.user)
        # all other cases covered by has_object_permission()
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.role == "SuperAdmins":
            return True

        queryset = Msgrcpt.objects
        if request.user.role == "DomainAdmins":
            domains = (
                Domain.objects
                .get_for_admin(request.user)
                .values_list("name", flat=True)
            )
            domains = [
                ".".join(domain.split(".")[::-1])
                for domain in domains
            ]
            filter_ = (
                Q(mail_id=obj.mail_id) &
                Q(rid__domain__in=domains)
            )
        else:
            rcpts = [request.user.email]
            if hasattr(request.user, "mailbox"):
                rcpts += request.user.mailbox.alias_addresses
            query_rcpts = []
            for rcpt in rcpts:
                query_rcpts += make_query_args(
                    rcpt, exact_extension=False, wildcard=".*"
                )
            re = "^(%s)$" % "|".join(query_rcpts)
            queryset = queryset.annotate(str_email=ConvertFrom("rid__email"))
            filter_ = (
                Q(mail_id=obj.mail_id) &
                Q(str_email__regex=re)
            )

        return queryset.filter(filter_).exists()
