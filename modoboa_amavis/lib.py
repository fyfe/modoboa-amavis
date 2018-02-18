# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import re
import socket
import string
import struct
import subprocess
from email.utils import parseaddr
from functools import wraps

import idna
from six.moves.urllib.parse import unquote

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse
from django.utils import six
from django.utils.translation import ugettext as _

from modoboa.admin import models as admin_models
from modoboa.core import models as core_models
from modoboa.lib.email_utils import (
    split_address, split_local_part, split_mailbox
)
from modoboa.lib.exceptions import InternalError
from modoboa.lib.sysutils import exec_cmd
from modoboa.lib.web_utils import NavigationParameters
from modoboa.parameters import tools as param_tools
from modoboa_amavis.models import Policy, Users
from modoboa_amavis.utils import (
    force_bytes, force_text, smart_bytes, smart_text
)


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


class AmavisReleaseClient(object):
    """A simple client to release messages from amavis quarantine.

    See https://amavis.org/README.protocol.txt"""
    _RE_OK_RESPONSE = re.compile(r"250 [\d\.]+ Ok")
    _RELEASE_REQUEST = """request=release
mail_id=%(mail_id)s
secret_id=%(secret_id)s
quar_type=Q
requested_by=%(requested_by)s

"""

    def __init__(self, user):
        """Initialise the amavis release client.

        user is an instance of modoboa.core.models.User representing the logged
        in user releasing the message or for self-service release the recipient
        email address.
        When a message is released amavis will add a Resent-From header
        containing `email`."""
        if isinstance(user, core_models.User):
            self.requested_by = user.email
        else:
            self.requested_by = user
        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
        try:
            if conf["am_pdp_mode"] == "inet":
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((conf["am_pdp_host"], conf["am_pdp_port"]))
            else:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.connect(conf["am_pdp_socket"])
        except socket.error as exc:
            six.raise_from(
                AmavisReleaseError(
                    _("Connection to Amavis failed."),
                    amavis_error=str(exc)
                ),
                exc
            )

    def release(self, mail_id, secret_id, recipient):
        """Release a message from quarantine."""
        request = force_bytes(
            self._RELEASE_REQUEST %
            {
                "mail_id": mail_id,
                "secret_id": secret_id,
                "recipient": recipient,
                "requested_by": self.requested_by,
            }
        )
        self.sock.send(request)
        answer = self.sock.recv(1024)
        answer = unquote(force_text(answer))

        if not self._RE_OK_RESPONSE.search(answer):
            raise AmavisReleaseError(
                _("Unable to release message."),
                mail_id=mail_id,
                amavis_error=answer
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.sock is not None:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            self.sock = None

        return exc_type is None


class AmavisReleaseError(Exception):
    def __init__(self, message, mail_id=None, amavis_error=None):
        super(AmavisReleaseError, self).__init__(message)
        self.mail_id = mail_id
        self.amavis_error = amavis_error


class SpamAssassinClient(object):
    """Learn ham/spam using SpamAssassin.

    SpamAssassin will use the database defined in Policy.sa_username

    This can be used as a context manager, when done it will call sync for any
    databases that were modified.

    with SpamAssassinClient(user, recipient_db) as sac:
        sac.learn(mark_as, rcpt, message)
    """
    _policy_cache = {}
    _db_to_sync = []
    _setup_cache = []

    def __init__(self, user, recipient_db):
        self.user = user
        self.recipient_db = recipient_db

        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
        self._sa_is_local = conf["sa_is_local"]
        self._spamd_host = conf["spamd_address"]
        self._spamd_port = conf["spamd_port"]
        self._manual_learning = conf["manual_learning"]
        self._domain_level_learning = conf["domain_level_learning"]
        self._user_level_learning = conf["user_level_learning"]
        self._default_username = conf["default_user"]

        search_path = getattr(settings, "SA_LOOKUP_PATH", [])
        self._command_name = "sa-learn" if conf["sa_is_local"] else "spamc"
        # TODO: replace with modoboa.lib.sysutils.which
        self._command = self._find_command(
            self._command_name, search_path=search_path)
        if self._command is None:
            raise SpamAssassinError(
                _("Failed to find %(command)s")
                % {"command": self._command_name}
            )

    def learn(self, mark_as, rcpt, message):
        if mark_as not in ["ham", "spam"]:
            raise ValueError("mark_as should be either ham or spam")

        if not self._manual_learning:
            raise SpamAssassinError(_("Manual learning is disabled."))

        sa_username = self._get_sa_username(rcpt)
        self._learn(mark_as, sa_username, message)
        return sa_username

    def _sync(self, username):
        if not self._sa_is_local:
            return

        command = [
            self._command,
            "-u", username,
            "--sync"
        ]

        # return_code, output = exec_cmd(" ".join(command))
        # if return_code != 0:
        #     raise SpamAssassinError(
        #         _("unable to sync SpamAssassin database for %(username)s")
        #         % {"username": username},
        #         username=username,
        #         sa_error=output
        #     )

        try:
            popen_checkcall(command)
        except CalledProcessError as exc:
            six.raise_from(
                SpamAssassinError(
                    _("unable to sync SpamAssassin database for %(username)s")
                    % {"username": username},
                    username=username,
                    sa_error=exc.stderr
                ),
                exc
            )

    def _find_command(self, command_name, search_path=None):
        """Search for the sa-learn/spamc command."""
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
        fpath, fname = os.path.split(command_name)
        if fpath:
            if is_exe(command_name):
                return command_name
        else:
            if not search_path:
                search_path = os.environ["PATH"].split(os.pathsep)
            for path in search_path:
                exe_file = os.path.join(path, command_name)
                if is_exe(exe_file):
                    return exe_file
        return None

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

        # message = force_bytes(message)
        # return_code, output = exec_cmd(force_bytes(" ".join(command)), pinput=message)
        # if not self._sa_is_local and return_code in [5, 6]:
        #     # spamc return codes:
        #     #     5 - message was learned
        #     #     6 - already learned
        #     pass
        # elif return_code != 0:
        #     raise SpamAssassinError(
        #         _("unable to learn %(mark_as)s for %(username)s")
        #         % {"mark_as": mark_as, "username": username},
        #         username=username,
        #         sa_error=output
        #     )

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
                        username=username,
                        sa_error=exc.stderr
                    ),
                    exc
                )

        if self._sa_is_local and username not in self._db_to_sync:
            self._db_to_sync += username

    def _get_sa_username(self, email):
        if self.user.role in ["SuperAdmins", "DomainAdmins"]:
            # Only SuperAdmins and DomainAdmins can do manual learning for
            # messages to other users.
            if self.recipient_db == "global":
                username = self._default_username
            elif self.recipient_db == "domain":
                domain = self._get_domain_from_rcpt(email)
                username = domain.name
                if username not in self._setup_cache:
                    setup_manual_learning_for_domain(domain)
                    self._setup_cache.append(username)
            else:
                mailbox = self._get_mailbox_from_rcpt(email)
                if mailbox is None:
                    username = self._default_username
                else:
                    if isinstance(mailbox, admin_models.Mailbox):
                        username = mailbox.full_address
                    elif isinstance(mailbox, admin_models.AliasRecipient):
                        username = mailbox.address
                    else:
                        username = self._default_username

                    if (
                        username != self._default_username and
                        username not in self._setup_cache
                    ):
                        setup_manual_learning_for_mbox(self.user.mailbox)
                        self._setup_cache.append(username)
        else:
            username = self.user.email
            if username not in self._setup_cache:
                setup_manual_learning_for_mbox(self.user.mailbox)
                self._setup_cache.append(username)

        return username

    def _get_domain_from_rcpt(self, rcpt):
        """Retrieve a domain from a recipient address."""
        local_part, domain = split_address(rcpt)
        try:
            domain = admin_models.Domain.objects.get(name=domain)
        except admin_models.Domain.DoesNotExist:
            raise SpamAssassinError(_("Local domain not found"))
        return domain

    def _get_mailbox_from_rcpt(self, rcpt):
        """Retrieve a mailbox from a recipient address."""
        local_part, domain = split_address(rcpt)
        local_part, extension = split_local_part(local_part)
        try:
            mailbox = (
                admin_models.Mailbox.objects
                .select_related("domain")
                .get(address=local_part, domain__name=domain)
            )
        except admin_models.Mailbox.DoesNotExist:
            try:
                alias = (
                    admin_models.Alias.objects
                    .get(
                        address="%s@%s" % (local_part, domain),
                        aliasrecipient__r_mailbox__isnull=False
                    )
                )
            except admin_models.Alias.DoesNotExist:
                raise SpamAssassinError(_("No recipient found"))
            else:
                if alias.type == "alias":
                    mailbox = alias.aliasrecipient_set\
                        .filter(r_mailbox__isnull=False)\
                        .first()
                else:
                    mailbox = None
        return mailbox

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for username in self._db_to_sync:
            # if SA user database was updated sync it
            self._sync(username)

        return exc_type is None


class SpamAssassinError(Exception):
    def __init__(self, message, username=None, sa_error=None):
        super(SpamAssassinError, self).__init__(message)
        self.username = username
        self.sa_error = sa_error


class AMrelease(object):
    def __init__(self):
        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
        try:
            if conf["am_pdp_mode"] == "inet":
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((conf["am_pdp_host"], conf["am_pdp_port"]))
            else:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.connect(conf["am_pdp_socket"])
        except socket.error as err:
            raise InternalError(
                _("Connection to amavis failed: %s" % str(err))
            )

    def decode(self, answer):
        def repl(match):
            return struct.pack("B", string.atoi(match.group(0)[1:], 16))

        return re.sub(br"%([0-9a-fA-F]{2})", repl, answer)

    def __del__(self):
        self.sock.close()

    def sendreq(self, mailid, secretid, recipient, *others):
        self.sock.send(smart_bytes("""request=release
mail_id=%s
secret_id=%s
quar_type=Q
recipient=%s

""" % (mailid, secretid, recipient)))
        answer = self.sock.recv(1024)
        answer = self.decode(answer)
        if re.search(br"250 [\d\.]+ Ok", answer):
            return True
        return False


class OLDSpamassassinClient(object):
    """A stupid spamassassin client."""

    def __init__(self, user, recipient_db):
        """Constructor."""
        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
        self._sa_is_local = conf["sa_is_local"]
        self._default_username = conf["default_user"]
        self._recipient_db = recipient_db
        self._setup_cache = {}
        self._username_cache = []
        if user.role == "SimpleUsers":
            if conf["user_level_learning"]:
                self._username = user.email
        else:
            self._username = None
        self.error = None
        if self._sa_is_local:
            self._learn_cmd = self._find_binary("sa-learn")
            self._learn_cmd += " --{0} --no-sync -u {1}"
            self._learn_cmd_kwargs = {}
            self._expected_exit_codes = [0]
            self._sync_cmd = self._find_binary("sa-learn")
            self._sync_cmd += " -u {0} --sync"
        else:
            self._learn_cmd = self._find_binary("spamc")
            self._learn_cmd += " -d {0} -p {1}".format(
                conf["spamd_address"], conf["spamd_port"]
            )
            self._learn_cmd += " -L {0} -u {1}"
            self._learn_cmd_kwargs = {}
            self._expected_exit_codes = [5, 6]

    def _find_binary(self, name):
        """Find path to binary."""
        code, output = exec_cmd("which {}".format(name))
        if not code:
            return smart_text(output).strip()
        known_paths = getattr(settings, "SA_LOOKUP_PATH", ("/usr/bin", ))
        for path in known_paths:
            bpath = os.path.join(path, name)
            if os.path.isfile(bpath) and os.access(bpath, os.X_OK):
                return bpath
        raise InternalError(_("Failed to find {} binary").format(name))

    def _get_mailbox_from_rcpt(self, rcpt):
        """Retrieve a mailbox from a recipient address."""
        local_part, domname, extension = (
            split_mailbox(rcpt, return_extension=True))
        try:
            mailbox = admin_models.Mailbox.objects.select_related(
                "domain").get(address=local_part, domain__name=domname)
        except admin_models.Mailbox.DoesNotExist:
            alias = admin_models.Alias.objects.filter(
                address="{}@{}".format(local_part, domname),
                aliasrecipient__r_mailbox__isnull=False).first()
            if not alias:
                raise InternalError(_("No recipient found"))
            if alias.type != "alias":
                return None
            mailbox = alias.aliasrecipient_set.filter(
                r_mailbox__isnull=False).first()
        return mailbox

    def _get_domain_from_rcpt(self, rcpt):
        """Retrieve a domain from a recipient address."""
        local_part, domname = split_mailbox(rcpt)
        domain = admin_models.Domain.objects.filter(name=domname).first()
        if not domain:
            raise InternalError(_("Local domain not found"))
        return domain

    def _learn(self, rcpt, msg, mtype):
        """Internal method to call the learning command."""
        if self._username is None:
            if self._recipient_db == "global":
                username = self._default_username
            elif self._recipient_db == "domain":
                domain = self._get_domain_from_rcpt(rcpt)
                username = domain.name
                condition = (
                    username not in self._setup_cache and
                    setup_manual_learning_for_domain(domain))
                if condition:
                    self._setup_cache[username] = True
            else:
                mbox = self._get_mailbox_from_rcpt(rcpt)
                if mbox is None:
                    username = self._default_username
                else:
                    if isinstance(mbox, admin_models.Mailbox):
                        username = mbox.full_address
                    elif isinstance(mbox, admin_models.AliasRecipient):
                        username = mbox.address
                    else:
                        username = None
                    condition = (
                        username is not None and
                        username not in self._setup_cache and
                        setup_manual_learning_for_mbox(mbox))
                    if condition:
                        self._setup_cache[username] = True
        else:
            username = self._username
            if username not in self._setup_cache:
                mbox = self._get_mailbox_from_rcpt(username)
                if mbox and setup_manual_learning_for_mbox(mbox):
                    self._setup_cache[username] = True
        if username not in self._username_cache:
            self._username_cache.append(username)
        cmd = self._learn_cmd.format(mtype, username)
        code, output = exec_cmd(
            cmd, pinput=smart_bytes(msg), **self._learn_cmd_kwargs)
        if code in self._expected_exit_codes:
            return True
        self.error = smart_text(output)
        return False

    def learn_spam(self, rcpt, msg):
        """Learn new spam."""
        return self._learn(rcpt, msg, "spam")

    def learn_ham(self, rcpt, msg):
        """Learn new ham."""
        return self._learn(rcpt, msg, "ham")

    def done(self):
        """Call this method at the end of the processing."""
        if self._sa_is_local:
            for username in self._username_cache:
                cmd = self._sync_cmd.format(username)
                exec_cmd(cmd, **self._learn_cmd_kwargs)


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


def create_user_and_policy(name, priority=7):
    """Create records.

    Create two records (a user and a policy) using :keyword:`name` as
    an identifier.

    :param str name: name
    :return: the new ``Policy`` object
    """
    if Users.objects.filter(email=name).exists():
        return Policy.objects.get(policy_name=name[:32])
    policy = Policy.objects.create(policy_name=name[:32])
    Users.objects.create(
        email=name, fullname=name, priority=priority, policy=policy
    )
    return policy


def create_user_and_use_policy(name, policy, priority=7):
    """Create a *users* record and use an existing policy.

    :param str name: user record name
    :param str policy: string or Policy instance
    """
    if isinstance(policy, six.string_types):
        policy = Policy.objects.get(policy_name=policy[:32])
    Users.objects.get_or_create(
        email=name, fullname=name, priority=priority, policy=policy
    )


def update_user_and_policy(oldname, newname):
    """Update records.

    :param str oldname: old name
    :param str newname: new name
    """
    if oldname == newname:
        return
    u = Users.objects.get(email=oldname)
    u.email = newname
    u.fullname = newname
    u.policy.policy_name = newname[:32]
    u.policy.save(update_fields=["policy_name"])
    u.save()


def delete_user_and_policy(name):
    """Delete records.

    :param str name: identifier
    """
    try:
        u = Users.objects.get(email=name)
    except Users.DoesNotExist:
        return
    u.policy.delete()
    u.delete()


def delete_user(name):
    """Delete a *users* record.

    :param str name: user record name
    """
    try:
        Users.objects.get(email=name).delete()
    except Users.DoesNotExist:
        pass


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


def setup_manual_learning_for_domain(domain):
    """Setup manual learning if necessary.

    :return: True if learning has been setup, False otherwise
    """
    if Policy.objects.filter(sa_username=domain.name).exists():
        return False
    policy = Policy.objects.get(policy_name="@{}".format(domain.name[:32]))
    policy.sa_username = domain.name
    policy.save()
    return True


def setup_manual_learning_for_mbox(mbox):
    """Setup manual learning if necessary.

    :return: True if learning has been setup, False otherwise
    """
    result = False
    if (isinstance(mbox, admin_models.AliasRecipient) and
            mbox.r_mailbox is not None):
        mbox = mbox.r_mailbox
    if isinstance(mbox, admin_models.Mailbox):
        pname = mbox.full_address[:32]
        if not Policy.objects.filter(policy_name=pname).exists():
            policy = create_user_and_policy(pname)
            policy.sa_username = mbox.full_address
            policy.save()
            for alias in mbox.alias_addresses:
                create_user_and_use_policy(alias, policy)
            result = True
    return result


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
        domain = idna.encode(domain, uts46=True).decode("ascii")
    delimiter = conf["recipient_delimiter"]
    local_part, extension = split_local_part(local_part, delimiter=delimiter)
    query_args = []
    if (
        conf["localpart_is_case_sensitive"] or
        (domain and domain != orig_domain)
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


def cleanup_email_address(address):
    address = parseaddr(address)
    if address[0]:
        return "%s <%s>" % address
    return address[1]


def popen_checkcall(args, data_in=None):
    """
    Adapted from Py3 subprocess.checkcall().
    subprocess.run() where are thou? :( Py >=3.5 only)
    """
    proc = None
    out = None
    err = None
    try:
        if data_in is None:
            proc = subprocess.Popen(args)
            proc.wait()
        else:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE)
            out, err = proc.communicate(input=force_bytes(data_in))
    except Exception as exc:
        if proc is not None:
            proc.kill()
            proc.wait()
        six.raise_from(
            CalledProcessError(proc.returncode, args, out, err),
            exc
        )
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        out, err = proc.communicate()
        six.raise_from(
            CalledProcessError(proc.returncode, args, out, err),
            exc
        )

    if proc.returncode:
        raise CalledProcessError(proc.returncode, args, out, err)

    return 0


class CalledProcessError(Exception):

    def __init__(self, returncode, cmd, stdout, stderr):
        self.returncode = returncode
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr
        super(CalledProcessError, self).__init__()
