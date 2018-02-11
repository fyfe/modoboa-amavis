# -*- coding: utf-8 -*-

"""Admin API urls."""

from __future__ import unicode_literals

from rest_framework import routers

from modoboa_amavis.api import viewsets

router = routers.SimpleRouter()

router.register(
    r"quarantine", viewsets.QuarantineViewSet, base_name="quarantine"
)

urlpatterns = router.urls
