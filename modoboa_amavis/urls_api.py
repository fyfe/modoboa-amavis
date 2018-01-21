# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from rest_framework import routers

from . import api


router = routers.SimpleRouter()
router.register(r"bwl", api.BlackWhiteListViewSet, base_name="api-bwl")
urlpatterns = router.urls
