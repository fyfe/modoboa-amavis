# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import socket

import mock

from django.test import override_settings
from django.utils.translation import ugettext as _

from modoboa.admin import factories as admin_factories
from modoboa.core import models as core_models
from modoboa.core import factories as core_factories
from modoboa.lib.tests import ModoTestCase

from modoboa_amavis.lib import make_query_args
from modoboa_amavis.lib.spamassassin_client import (
    PolicyError, SpamAssassinClient, SpamAssassinError
)
from modoboa_amavis.lib.amavis_release_client import (
    AmavisError, AmavisReleaseClient
)
from modoboa_amavis.models import policy as policy_models
from modoboa_amavis.utils import smart_bytes, smart_text


class MakeQueryArgsTests(ModoTestCase):

    """Tests for modoboa_amavis.lib.make_query_args()."""

    def test_simple_email_address_001(self):
        """Check case insensitive email address without recipient delimiter."""
        self.set_global_parameter("localpart_is_case_sensitive", False)
        self.set_global_parameter("recipient_delimiter", "")
        address = "User+Foo@sub.exAMPLE.COM"
        expected_output = [
            "user+foo@sub.example.com",
        ]
        output = make_query_args(address)
        self.assertEqual(output, expected_output)

    def test_simple_email_address_002(self):
        """Check case sensitive email address with recipient delimiter."""
        self.set_global_parameter("localpart_is_case_sensitive", True)
        self.set_global_parameter("recipient_delimiter", "+")
        address = "User+Foo@sub.exAMPLE.COM"
        expected_output = [
            "User+Foo@sub.exAMPLE.COM",
            "User+Foo@sub.example.com",
            "User@sub.example.com",
        ]
        output = make_query_args(address)
        self.assertEqual(output, expected_output)

    def test_simple_email_address_003(self):
        """Check email address with recipient delimiter wildcard."""
        self.set_global_parameter("localpart_is_case_sensitive", False)
        self.set_global_parameter("recipient_delimiter", "+")
        address = "User+Foo@sub.exAMPLE.COM"
        expected_output = [
            "user+foo@sub.example.com",
            "user+.*@sub.example.com",
            "user@sub.example.com",
        ]
        output = make_query_args(address, exact_extension=False, wildcard=".*")
        self.assertEqual(output, expected_output)

    def test_simple_email_address_004(self):
        """Check domain search."""
        self.set_global_parameter("localpart_is_case_sensitive", False)
        self.set_global_parameter("recipient_delimiter", "+")
        address = "User+Foo@sub.exAMPLE.COM"
        expected_output = [
            "user+foo@sub.example.com",
            "user+.*@sub.example.com",
            "user@sub.example.com",
            "@sub.example.com",
            "@.",
        ]
        output = make_query_args(
            address, exact_extension=False, wildcard=".*", domain_search=True)
        self.assertEqual(output, expected_output)

    def test_simple_email_address_idn(self):
        """Check email address with international domain name."""
        self.set_global_parameter("localpart_is_case_sensitive", False)
        self.set_global_parameter("recipient_delimiter", "")
        address = "Pingüino@Pájaro.Niño.exAMPLE.COM"
        expected_output = [
            "Pingüino@Pájaro.Niño.exAMPLE.COM",
            "pingüino@xn--pjaro-xqa.xn--nio-8ma.example.com",
        ]
        output = make_query_args(address)
        self.assertEqual(output, expected_output)


@override_settings(SA_LOOKUP_PATH=(os.path.dirname(__file__), ))
class SpamAssassinClientTests(ModoTestCase):

    """Tests for SpamAssassinClient."""

    @classmethod
    def setUpTestData(cls):  # noqa:N802
        """Create initial test data."""
        super(SpamAssassinClientTests, cls).setUpTestData()
        cls.domain = admin_factories.DomainFactory(name="example.com")
        cls.simpleuser = core_factories.UserFactory.create(
            username="user@example.com", groups=("SimpleUsers",),
        )
        admin_factories.MailboxFactory.create(
            address="user", domain=cls.domain, user=cls.simpleuser
        )

    def _test_learn(self, mark_as, rcpt, expect_sa_username, domain, user):
        self.set_global_parameter("sa_is_local", True)
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("domain_level_learning", domain)
        self.set_global_parameter("user_level_learning", user)
        with SpamAssassinClient() as sa_client:
            sa_username = sa_client.learn(mark_as, rcpt, b"")
        self.assertEqual(sa_username, expect_sa_username)

    def test_learn_spam(self):
        """Learn a spam message."""
        self._test_learn(
            "spam", self.simpleuser.username, self.simpleuser.username,
            True, True
        )

    def test_learn_ham(self):
        """Learn a ham message."""
        self._test_learn(
            "ham", self.simpleuser.username, self.simpleuser.username,
            True, True
        )

    def test_learn_global_level(self):
        """Test global level learning."""
        self.set_global_parameter("default_user", "amavis")
        expect_sa_username = "amavis"
        self._test_learn(
            "spam", self.simpleuser.username, expect_sa_username,
            False, False
        )

    def test_learn_domain_level(self):
        """Test domain level learning."""
        expect_sa_username = "@%s" % self.domain.name
        self._test_learn(
            "spam", self.simpleuser.username, expect_sa_username,
            True, False
        )

    def test_manual_learning_disabled(self):
        """Check a SpamAssassinError is raise if manual learning is disabled."""
        self.set_global_parameter("manual_learning", False)
        with self.assertRaises(SpamAssassinError) as ctx:
            SpamAssassinClient().learn("spam", "user@example.com", b"")

        expexted_error = _("Manual learning is disabled.")
        self.assertEqual(smart_text(ctx.exception), expexted_error)

    @override_settings(SA_LOOKUP_PATH=[])
    def test_sa_programs_missing(self):
        """Check a SpamAssassinError is raise if SA programs can't be found."""
        self.set_global_parameter("sa_is_local", True)
        with self.assertRaises(SpamAssassinError) as ctx:
            SpamAssassinClient()

        expexted_error = (
            _("Failed to find %(command)s")
            % {"command": "sa-learn"}
        )
        self.assertEqual(smart_text(ctx.exception), expexted_error)


@override_settings(SA_LOOKUP_PATH=(os.path.dirname(__file__), ))
class SpamAssassinClientNoPoliciesTests(ModoTestCase):

    """Tests with no policies.

    This test is isolated because it requires all User/Policy objects to be
    deleted."""

    @classmethod
    def setUpTestData(cls):  # noqa:N802
        """Delete all existing User/Policy objects."""
        super(SpamAssassinClientNoPoliciesTests, cls).setUpTestData()
        policy_models.User.objects.all().delete()
        policy_models.Policy.objects.all().delete()

    def test_no_policies(self):
        """Check a PolicyError is raised when a Policy can't be found."""
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("user_level_learning", True)
        with self.assertRaises(PolicyError) as ctx:
            with SpamAssassinClient() as sa_client:
                sa_client.learn("spam", "user@example.com", b"")

        expected_error = (
            _("unable to find a policy to match %(email)s")
            % {"email": "user@example.com"}
        )
        self.assertEqual(smart_text(ctx.exception), expected_error)


class AmavisReleaseClientTests(ModoTestCase):

    """Tests for AmavisReleaseClient."""

    @classmethod
    def setUpTestData(cls):  # noqa:N802
        """Create initial test data."""
        super(AmavisReleaseClientTests, cls).setUpTestData()
        cls.admin = core_models.User.objects.get(username="admin")

    @mock.patch("socket.socket")
    def test_connection_failure(self, mock_socket):
        """Check AmavisError is raised on connection failure."""
        mock_socket.side_effect = socket.error()
        with self.assertRaises(AmavisError):
            AmavisReleaseClient(self.admin)

    @mock.patch("socket.socket")
    def test_release_with_user(self, mock_socket):
        """Check message release with user."""
        mock_socket.return_value.recv.return_value = (
            b"250 2.5.0 Ok,%20id=MWZmu9Di,%20continue%20delivery\r\n"
        )
        with AmavisReleaseClient(self.admin) as ar_client:
            ar_client.release(smart_bytes("mail_id"), smart_bytes("secret_id"))

    @mock.patch("socket.socket")
    def test_release_with_rcpt(self, mock_socket):
        """Check message release with recipient (self service)."""
        mock_socket.return_value.recv.return_value = (
            b"250 2.5.0 Ok,%20id=MWZmu9Di,%20continue%20delivery\r\n"
        )
        with AmavisReleaseClient("user@example.com") as ar_client:
            ar_client.release("mail_id", "secret_id")

    @mock.patch("socket.socket")
    def test_release_failure(self, mock_socket):
        """Check AmavisError is raised on release failure."""
        mock_socket.return_value.recv.return_value = (
            b"451 4.5.0 Error%20in%20processing,%20id=mail_id\r\n"
        )
        with self.assertRaises(AmavisError) as ctx:
            with AmavisReleaseClient(self.admin) as ar_client:
                ar_client.release("mail_id", "secret_id")

        expected_error = "451 4.5.0 Error in processing, id=mail_id\r\n"
        self.assertEqual(ctx.exception.error, expected_error)
