# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from functools import wraps

import idna

from django.contrib.auth.views import redirect_to_login
from django.urls import reverse
from django.utils import six

from modoboa.lib.email_utils import split_address, split_local_part
from modoboa.lib.web_utils import NavigationParameters
from modoboa.parameters import tools as param_tools


def selfservice(ssfunc=None):
    """Decorator used to expose views to the 'self-service' feature

    The 'self-service' feature allows users to act on quarantined
    messages without beeing authenticated.

    This decorator only acts as a 'router'.

    :param ssfunc: the function to call if the 'self-service'
                   pre-requisites are satisfied
    """
    def decorator(f):
        @wraps(f)
        def wrapped_f(request, *args, **kwargs):
            secret_id = request.GET.get("secret_id")
            if not secret_id and request.user.is_authenticated:
                return f(request, *args, **kwargs)
            if not param_tools.get_global_parameter("self_service"):
                return redirect_to_login(
                    reverse("modoboa_amavis:index")
                )
            return ssfunc(request, *args, **kwargs)
        return wrapped_f
    return decorator


class QuarantineNavigationParameters(NavigationParameters):
    """
    Specific NavigationParameters subclass for the quarantine.
    """
    def __init__(self, request):
        super(QuarantineNavigationParameters, self).__init__(
            request, "quarantine_navparams"
        )
        self.parameters += [
            ("pattern", "", False),
            ("criteria", "from_addr", False),
            ("msgtype", None, False),
            ("viewrequests", None, False)
        ]

    def _store_page(self):
        """Specific method to store the current page."""
        if self.request.GET.get("reset_page", None) or "page" not in self:
            self["page"] = 1
        else:
            page = self.request.GET.get("page", None)
            if page is not None:
                self["page"] = int(page)

    def back_to_listing(self):
        """Return the current listing URL.

        Looks into the user's session and the current request to build
        the URL.

        :return: a string
        """
        url = "listing"
        params = []
        navparams = self.request.session[self.sessionkey]
        if "page" in navparams:
            params += ["page=%s" % navparams["page"]]
        if "order" in navparams:
            params += ["sort_order=%s" % navparams["order"]]
        params += ["%s=%s" % (p[0], navparams[p[0]])
                   for p in self.parameters if p[0] in navparams]
        if params:
            url += "?%s" % ("&".join(params))
        return url


def manual_learning_enabled(user):
    """Check if manual learning is enabled or not.

    Also check for :kw:`user` if necessary.

    :return: True if learning is enabled, False otherwise.
    """
    conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
    if not conf["manual_learning"]:
        return False
    if user.role != "SuperAdmins":
        if user.has_perm("admin.view_domains"):
            manual_learning = (
                conf["domain_level_learning"] or conf["user_level_learning"])
        else:
            manual_learning = conf["user_level_learning"]
        return manual_learning
    return True


def make_query_args(address, exact_extension=True, wildcard=None,
                    domain_search=False):
    assert isinstance(address, six.text_type),\
        "address should be of type %s" % six.text_type.__name__
    conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
    local_part, domain = split_address(address)
    if not conf["localpart_is_case_sensitive"]:
        local_part = local_part.lower()
    if domain:
        domain = domain.lstrip("@").rstrip(".")
        domain = domain.lower()
        orig_domain = domain
        domain = idna.encode(domain, uts46=True).decode('ascii')
    delimiter = conf["recipient_delimiter"]
    local_part, extension = split_local_part(local_part, delimiter=delimiter)
    query_args = []
    if (
        conf["localpart_is_case_sensitive"]
        or (domain and domain != orig_domain)
    ):
        query_args.append(address)
    if extension:
        query_args.append("%s%s%s@%s" % (
            local_part, delimiter, extension, domain))
    if delimiter and not exact_extension and wildcard:
        query_args.append("%s%s%s@%s" % (
            local_part, delimiter, wildcard, domain))
    query_args.append("%s@%s" % (local_part, domain))
    if domain_search:
        query_args.append("@%s" % domain)
        query_args.append("@.")

    return query_args
