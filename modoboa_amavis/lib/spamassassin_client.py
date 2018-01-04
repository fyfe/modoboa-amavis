# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf import settings
from django.db.models import Q
from django.utils import six
from django.utils.translation import ugettext as _

from modoboa.lib.email_utils import split_address
from modoboa.parameters import tools as param_tools

from modoboa_amavis.models import policy as policy_models
from modoboa_amavis.lib import make_query_args
from modoboa_amavis.lib.move_to_modoboa import (
    which, popen_checkcall, CalledProcessError
)
from modoboa_amavis.utils import ConvertFrom


class SpamAssassinClient(object):
    """Learn ham/spam using SpamAssassin.

    SpamAssassin will use the database defined in Policy.sa_username

    This can be used as a context manager, when done it will call sync for any
    databases that were modified.

    with SpamAssassinClient() as sa_client:
        sa_client.learn(mark_as, rcpt, message)
    """
    _sa_username_cache = {}
    _db_to_sync = []

    def __init__(self):
        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
        self._sa_is_local = conf["sa_is_local"]
        self._spamd_host = conf["spamd_address"]
        self._spamd_port = conf["spamd_port"]
        self._manual_learning = conf["manual_learning"]
        self._domain_level_learning = conf["domain_level_learning"]
        self._user_level_learning = conf["user_level_learning"]
        self._default_user = conf["default_user"]

        search_path = getattr(settings, "SA_LOOKUP_PATH", [])
        self._command_name = "sa-learn" if conf["sa_is_local"] else "spamc"
        self._command = which(self._command_name, search_path=search_path)
        if self._command is None:
            raise SpamAssassinError(
                _("Failed to find %(command)s")
                % {"command": self._command_name}
            )

    def learn(self, mark_as, rcpt, message):
        assert mark_as in ["ham", "spam"],\
            "mark_as should be either ham or spam"
        assert isinstance(rcpt, six.text_type),\
            "rcpt should be of type %s" % six.text_type.__name__
        assert isinstance(message, six.binary_type),\
            "message should be of type %s" % six.binary_type.__name__

        if not self._manual_learning:
            raise SpamAssassinError(_("Manual learning is disabled."))

        # This is UGLY!
        # The proper way to do it is to have policy.sa_username = None if
        # learning is disabled at that level (domain or user).
        # TODO: update sa_username when domain_level_learning or
        #       user_level_learning are changed and find a way to test it.
        if not (self._domain_level_learning or self._user_level_learning):
            sa_username = self._default_user
        elif not self._user_level_learning:
            local_part_, domain = split_address(rcpt)
            sa_username = self._get_sa_username("@%s" % domain)
        else:
            sa_username = self._get_sa_username(rcpt)

        self._learn(mark_as, sa_username, message)
        return sa_username

    def _learn(self, mark_as, username, message):
        command = [
            self._command,
            "-u", username,
        ]

        if self._sa_is_local:
            command += [
                "--%s" % mark_as,
                "--no-sync"
            ]
        else:
            command += [
                "-L", mark_as,
                "-d", self._spamd_host,
                "-p", "%d" % self._spamd_port,
            ]

        try:
            popen_checkcall(command, data_in=message)
        except CalledProcessError as exc:
            if not self._sa_is_local and exc.returncode in [5, 6]:
                # spamc return codes:
                #     5 - message was learned
                #     6 - already learned
                pass
            else:
                six.raise_from(
                    SpamAssassinError(
                        _("unable to learn %(mark_as)s for %(username)s")
                        % {"mark_as": mark_as, "username": username},
                        username=username),
                    exc)
        except Exception as exc:
            six.raise_from(
                SpamAssassinError(
                    _("unable to learn %(mark_as)s for %(username)s")
                    % {"mark_as": mark_as, "username": username},
                    username=username),
                exc)
        else:
            if self._sa_is_local and username not in self._db_to_sync:
                self._db_to_sync += username

    def _sync(self, username):
        if not self._sa_is_local:
            return

        command = [
            self._command,
            "-u", username,
            "--sync"
        ]

        try:
            popen_checkcall(command)
        except Exception as exc:
            six.raise_from(
                SpamAssassinError(
                    _("unable to sync SpamAssassin database for %(username)s")
                    % {"username": username},
                    username=username),
                exc)

    def _get_sa_username(self, email):
        """Find the SpamAssasin username from an Amavis policy for `email`

        Assuming email == user@example.com, search for an amavis user in the
        following order:
            user@example.com
            @example.com
            @. (catch all)
        """
        if email not in self._sa_username_cache:
            re_users = "^(%s)$" % "|".join(
                make_query_args(email, domain_search=True))
            policy_users = (
                policy_models.User.objects
                .annotate(str_email=ConvertFrom("email"))
                .order_by("-priority")
                .filter(Q(str_email__regex=re_users))
            )

            sa_username = None
            for user in policy_users:
                if user.policy.sa_username is not None:
                    sa_username = user.policy.sa_username
                    break

            if sa_username is not None:
                self._sa_username_cache[email] = sa_username
            else:
                raise PolicyError(
                    _("unable to find a policy to match %(email)s")
                    % {"email": email},
                    email=email
                )

        return self._sa_username_cache[email]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for username in self._db_to_sync:
            # if SA user database was updated sync it
            self._sync(username)

        return exc_type is None


class SpamAssassinError(Exception):
    def __init__(self, message, username=None, **kwargs):
        self.username = username
        super(SpamAssassinError, self).__init__(message, **kwargs)


class PolicyError(Exception):
    def __init__(self, message, email=None, **kwargs):
        self.email = email
        super(PolicyError, self).__init__(message, **kwargs)
