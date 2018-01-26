# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re
import socket

from six.moves.urllib.parse import unquote

from django.utils import six
from django.utils.translation import ugettext as _

from modoboa.core import models as core_models
from modoboa.parameters import tools as param_tools

from modoboa_amavis.utils import smart_bytes, smart_text


class AmavisReleaseClient(object):

    """A client to release messages from Amavis quarantine.

    See https://amavis.org/README.protocol.txt"""

    _RE_OK_RESPONSE = re.compile(r"250 [\d\.]+ Ok")
    _RELEASE_REQUEST = """request=release
mail_id=%(mail_id)s
secret_id=%(secret_id)s
quar_type=Q
requested_by=%(requested_by)s

"""

    def __init__(self, user):
        """Initialise the Amavis release client.

        user is an instance of modoboa.core.models.User representing the logged
        in user releasing the message or for self-service release the recipient
        email address.
        When a message is released Amavis will add a Resent-From header
        containing `email`."""
        if isinstance(user, core_models.User):
            self.released_by = user.email
        else:
            self.released_by = user
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
                AmavisError(
                    _("Connection to amavis failed. %(error_message)s")
                    % {"error_message": str(exc)},
                    error=str(exc)
                ),
                exc
            )

    def release(self, mail_id, secret_id):
        """Release a message from quarantine."""
        if not isinstance(mail_id, six.text_type):
            mail_id = smart_text(mail_id)
        if not isinstance(secret_id, six.text_type):
            secret_id = smart_text(secret_id)

        request = smart_bytes(
            self._RELEASE_REQUEST
            % {
                "mail_id": mail_id,
                "secret_id": secret_id,
                "requested_by": self.released_by,
            }
        )
        self.sock.send(request)
        answer = self.sock.recv(1024)
        answer = unquote(smart_text(answer))

        if not self._RE_OK_RESPONSE.search(answer):
            raise AmavisError(
                _("Unable to release message. [mail_id=%(mail_id)s]\n"
                  "Amavis responded with %(response)s")
                % {"mail_id": smart_text(mail_id), "response": answer},
                mail_id=mail_id,
                error=answer
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.sock is not None:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            self.sock = None

        return exc_type is None


class AmavisError(Exception):
    def __init__(self, message, mail_id=None, error=None, **kwargs):
        self.mail_id = mail_id
        self.error = error
        super(AmavisError, self).__init__(message, **kwargs)
