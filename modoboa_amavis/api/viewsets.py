# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime

from django.db.models import Q
from django.utils.translation import ugettext as _, ungettext

from rest_framework import serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import detail_route, list_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from modoboa.admin.models import Domain
from modoboa.parameters import tools as param_tools
from modoboa_amavis.api import pagination
from modoboa_amavis.api.permissions import AllowedQuarantineAccess
from modoboa_amavis.lib import (
    AmavisReleaseClient, AmavisReleaseError, SpamAssassinClient,
    SpamAssassinError, cleanup_email_address
)
from modoboa_amavis.models import Msgrcpt, Quarantine
from modoboa_amavis.sql_connector import make_query_args
from modoboa_amavis.sql_email import SQLemail
from modoboa_amavis.utils import ConvertFrom, fix_utf8_encoding, force_bytes


class QuarantineViewSet(viewsets.GenericViewSet):

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated, AllowedQuarantineAccess,)
    renderer_classes = (JSONRenderer, )

    queryset = Msgrcpt.objects.all()

    lookup_field = "mail_id"
    lookup_url_kwarg = "mail_id"
    lookup_value_regex = r"[\w\-\+]+"

    pagination_class = pagination.PageNumberPagination
    serializer_class = serializers.Serializer

    def filter_queryset(self, queryset):
        if self.action in ["list", "requests"]:
            filter_ = (
                self._apply_status_filter() &
                self._apply_user_filter()
            )
            queryset = (
                queryset
                .annotate(str_email=ConvertFrom("rid__email"))
                .filter(filter_)
            )
        return super(QuarantineViewSet, self).filter_queryset(queryset)

    def _apply_status_filter(self):
        if self.action == "requests":
            return Q(rs="p")
        else:
            # NOT marked for deletion AND NOT a clean message
            # TODO: Filtering out message currently being processed (rs == None)
            #       fails, needs looking into.
            return ~ Q(rs="D") & ~ Q(content="C")

    def _apply_user_filter(self):
        filter_ = Q(
            mail__in=Quarantine.objects.filter(chunk_ind=1).values("mail_id")
        )
        if self.request.user.role == "SuperAdmins":
            pass
        elif self.request.user.role == "DomainAdmins":
            domains = (
                Domain.objects
                .get_for_admin(self.request.user)
                .values_list("name", flat=True)
            )
            domains = [
                ".".join(domain.split(".")[::-1])
                for domain in domains
            ]
            filter_ = Q(rid__domain__in=domains)
        else:
            rcpts = [self.request.user.email]
            if hasattr(self.request.user, "mailbox"):
                rcpts += self.request.user.mailbox.alias_addresses
            query_rcpts = []
            for rcpt in rcpts:
                query_rcpts += make_query_args(
                    rcpt, exact_extension=False, wildcard=".*"
                )
            re = "^(%s)$" % "|".join(query_rcpts)
            filter_ = Q(str_email__regex=re)

        return filter_

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self._serialize_list_view(page)
            return self.get_paginated_response(data)

        data = self._serialize_list_view(queryset)
        return Response(data)

    @list_route(methods=["get"])
    def requests(self, request):
        return self.list(request)

    @staticmethod
    def _serialize_list_view(queryset):
        messages = []
        for msgrcpt in queryset:
            messages.append({
                "sender": cleanup_email_address(
                    fix_utf8_encoding(msgrcpt.mail.from_addr)
                ),
                "recipient": msgrcpt.rid.email,
                "subject": fix_utf8_encoding(msgrcpt.mail.subject),
                "mail_id": msgrcpt.mail_id,
                "date": datetime.datetime.fromtimestamp(
                    msgrcpt.mail.time_num
                ),
                "type": msgrcpt.content,
                "score": msgrcpt.bspam_level,
                "status": msgrcpt.rs,
            })
        return messages

    def retrieve(self, request, mail_id=None):
        msgrcpt = self.get_object()
        email = SQLemail(msgrcpt.mail_id, dformat="plain")
        headers = [
            (name, email.get_header(email.msg, name))
            for name in email.msg.keys()
        ]
        message = {
            "mail_id": msgrcpt.mail_id,
            "quarantine_type": email.qtype,
            "quarantine_reason": email.qreason,
            "headers": headers,
            "body": email.body,
        }
        return Response(message)

    @detail_route(methods=["post"])
    def mark_as_ham(self, request, mail_id=None):
        return self._mark_as(request, mark_as="ham", mail_id=mail_id)

    @detail_route(methods=["post"])
    def mark_as_spam(self, request, mail_id=None):
        return self._mark_as(request, mark_as="spam", mail_id=mail_id)

    def _mark_as(self, request, mark_as, mail_id):
        """Mark a message as ham/spam."""
        if "recipient_db" in request.data:
            recipient_db = request.data["recipient_db"]
        else:
            return Response(
                {
                    "detail": "recipient_db not specified",
                    "mail_id": mail_id,
                    "mark_as": mark_as,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if recipient_db not in ["global", "domain", "user"]:
            return Response(
                {
                    "detail": "recipient_db should be one of global, domain or "
                              "user",
                    "mail_id": mail_id,
                    "mark_as": mark_as,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        msgrcpt = self.get_object()
        mail_id = msgrcpt.mail_id
        rcpt = msgrcpt.mail.sid.email

        message_parts = (
            Quarantine.objects
            .filter(mail=msgrcpt.mail_id)
            .order_by("chunk_ind")
        )
        message = b"".join(
            force_bytes(part.mail_text) for part in message_parts
        )

        try:
            with SpamAssassinClient(request.user, recipient_db) as sac:
                sac.learn(mark_as, rcpt, message)
        except SpamAssassinError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "mail_id": mail_id,
                    "mark_as": mark_as,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        else:
            msgrcpt.rs = mark_as[0].upper()  # H or S
            msgrcpt.save(update_fields=["rs"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(methods=["post"])
    def release(self, request, mail_id=None):
        msgrcpt = self.get_object()
        try:
            self._release(request, msgrcpt)
        except AmavisReleaseError as exc:
            return Response(
                {
                    "detail": _("an error occured releasing quarantined "
                                "messages"),
                    "errors": [
                        {
                            "mail_id": exc.mail_id,
                            "amavis_error": exc.amavis_error,
                        }
                    ]
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @list_route(methods=["post"])
    def bulk_release(self, request):
        if "mail_id" not in request.data or len(request.data["mail_id"]) == 0:
            return Response(
                {"detail": "a list of mail_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        queryset = (
            self.filter_queryset(self.get_queryset())
            .filter(mail_id__in=request.data["mail_id"])
        )
        errors = []
        for msgrcpt in queryset:
            try:
                self._release(request, msgrcpt)
            except AmavisReleaseError as exc:
                errors.append(exc)

        if errors:
            return Response(
                {
                    "detail": _("an error occured releasing quarantined "
                                "messages"),
                    "errors": [
                        {
                            "mail_id": exc.mail_id,
                            "amavis_error": exc.amavis_error,
                        }
                        for exc in errors
                    ]
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _release(self, request, msgrcpt):
        if (
            request.user.role not in ["SuperAdmins", "DomainAdmins"] and
            not param_tools.get_global_parameter("user_can_release")
        ):
            msgrcpt.rs = "p"
            msgrcpt.save(update_fields=["rs"])
            return

        try:
            with AmavisReleaseClient(request.user) as arc:
                arc.release(
                    msgrcpt.mail_id, msgrcpt.mail.secret_id, msgrcpt.rid.email
                )
        except AmavisReleaseError as exc:
            raise
        else:
            msgrcpt.rs = "R"
            msgrcpt.save(update_fields=["rs"])

    @detail_route(methods=["post", "delete"])
    def delete(self, request, mail_id=None):
        msgrcpt = self.get_object()
        msgrcpt.rs = "D"
        msgrcpt.save(update_fields=["rs"])

        data = {
            "detail":
                _("%(count)d message deleted successfully")
                % {"count": 1},
            "mail_id": mail_id,
        }
        return Response(data)

    @list_route(methods=["post", "delete"])
    def bulk_delete(self, request):
        if "mail_id" not in request.data or len(request.data["mail_id"]) == 0:
            return Response(
                {"detail": "a list of mail_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        queryset = (
            self.filter_queryset(self.get_queryset())
            .filter(mail_id__in=request.data["mail_id"])
        )
        mail_id = []
        for msgrcpt in queryset:
            msgrcpt.rs = "D"
            msgrcpt.save(update_fields=["rs"])
            mail_id.append(msgrcpt.mail_id)
        data = {
            "detail":
                ungettext(
                    "%(count)d message deleted successfully",
                    "%(count)d messages deleted successfully",
                    len(mail_id)
                ) % {"count": len(mail_id)},
            "mail_id": mail_id,
        }
        return Response(data)
