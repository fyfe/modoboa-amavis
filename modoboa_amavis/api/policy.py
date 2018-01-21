# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db.models import Q

from rest_framework import viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions

from modoboa_amavis.lib import make_query_args
from modoboa_amavis.models import policy as policy_models
from modoboa_amavis.serializers import policy as policy_serializers
from modoboa_amavis.utils import ConvertFrom


class BlackWhiteListViewSet(viewsets.RetrieveUpdateDestroyAPIView):

    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    serializer_class = policy_serializers.BlackWhiteListSerializer

    def get_queryset(self):
        """Filter queryset based on current user."""
        queryset = super(BlackWhiteListViewSet, self).get_queryset()
        rcpts = [self.user.email]
        if hasattr(self.user, "mailbox"):
            rcpts += self.user.mailbox.alias_addresses

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

    def get_object(self):
        recipient, sender = policy_models.BlackWhiteList.id_to_email(
            self.kwargs["id"]
        )
        queryset = self.filter_queryset(self.get_queryset())
        filter_kwargs = {
            "recipient": recipient,
            "sender": sender,
        }
        obj = get_object_or_404(queryset, **filter_kwargs)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj
