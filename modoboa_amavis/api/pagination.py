# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import math

from rest_framework import pagination

from modoboa.parameters import tools as param_tools


class PageNumberPagination(pagination.PageNumberPagination):

    page_size_query_param = "page_size"
    max_page_size = 50

    _set_user_page_size = False

    def get_page_size(self, request):
        if not self._set_user_page_size:
            try:
                user_page_size = (
                    request.user.parameters.get_value("messages_per_page")
                )
                if user_page_size is not None:
                    self.page_size = pagination._positive_int(
                        user_page_size, strict=True, cutoff=self.max_page_size
                    )
            except (ValueError, param_tools.NotDefined):
                self.page_size = math.floor(self.max_page_size / 2)
            finally:
                self._set_user_page_size = True
        return super(PageNumberPagination, self).get_page_size(request)
