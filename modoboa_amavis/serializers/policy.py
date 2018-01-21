# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from rest_framework import serializers

from modoboa_amavis.models import policy as policy_models


class UserSerializer(serializers.ModelSerializer):

    """User serializer."""

    class Meta:
        model = policy_models.User
        fields = (
            "id", "priority", "policy", "email", "fullname",
        )


class SenderAddressSerializer(serializers.ModelSerializer):

    """SenderAddress serializer."""

    class Meta:
        model = policy_models.SenderAddress
        fields = (
            "id", "priority", "email",
        )


class BlackWhiteListSerializer(serializers.ModelSerializer):

    """BlackWhiteList serializer."""

    class Meta:
        model = policy_models.BlackWhiteList
        fields = (
            "recipient", "sender", "action_raw",
        )
