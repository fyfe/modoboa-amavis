# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

import mock

from django.test import SimpleTestCase, override_settings

from modoboa.admin import factories as admin_factories
from modoboa.core import factories as core_factories, models as core_models
from modoboa.lib.tests import ModoTestCase
from modoboa_amavis.lib import (
    AmavisReleaseClient, AmavisReleaseError, SpamAssassinClient,
    SpamAssassinError, cleanup_email_address, make_query_args
)
from modoboa_amavis.utils import force_bytes


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


class FixUTF8EncodingTests(SimpleTestCase):

    """Tests for modoboa_amavis.lib.cleanup_email_address()."""

    def test_value_with_newline(self):
        value = "\"John Smith\" <john.smith@example.com>\n"
        expected_output = "John Smith <john.smith@example.com>"
        output = cleanup_email_address(value)
        self.assertEqual(output, expected_output)

    def test_no_name(self):
        value = "<john.smith@example.com>"
        expected_output = "john.smith@example.com"
        output = cleanup_email_address(value)
        self.assertEqual(output, expected_output)


class AmavisReleaseClientTestCase(ModoTestCase):

    @mock.patch("socket.socket")
    def test_release(self, mock_socket):
        """release a message from quarantine."""
        mock_socket.return_value.recv.return_value = force_bytes(
            r"250 2.5.0 Ok,%20id={},%20continue%20delivery\r\n".format("mailid")
        )
        with AmavisReleaseClient("admin") as arc:
            arc.release("mailid", "secretid", "user@example.com")

    def test_release_connect_error(self):
        """ensure socket connection errors are caught."""
        self.set_global_parameter("am_pdp_mode", "inet")
        with self.assertRaises(AmavisReleaseError) as cm:
            with AmavisReleaseClient("admin") as arc:
                arc.release("mailid", "secretid", "user@example.com")
        self.assertIsNotNone(cm.exception.amavis_error)

    @mock.patch("socket.socket")
    def test_release_release_error(self, mock_socket):
        """ensure release errors are caught."""
        mock_socket.return_value.recv.return_value = force_bytes(
            r"451 4.5.0 Error%20in%20processing,%20id={}\r\n".format("mailid")
        )
        with self.assertRaises(AmavisReleaseError) as cm:
            with AmavisReleaseClient("admin") as arc:
                arc.release("mailid", "secretid", "user@example.com")
        self.assertIsNotNone(cm.exception.amavis_error)


@override_settings(SA_LOOKUP_PATH=(os.path.dirname(__file__), ))
class SpamAssassinClientTests(ModoTestCase):

    """Tests for SpamAssassinClient."""

    @classmethod
    def setUpTestData(cls):  # noqa:N802
        """Create initial test data."""
        super(SpamAssassinClientTests, cls).setUpTestData()
        cls.super_admin = core_models.User.objects.get(username="admin")
        cls.domain = admin_factories.DomainFactory(name="example.com")

        cls.domain_admin = core_factories.UserFactory.create(
            username="admin@example.com", groups=("DomainAdmins",),
        )
        admin_factories.MailboxFactory.create(
            address="admin", domain=cls.domain, user=cls.domain_admin
        )
        cls.domain.add_admin(cls.domain_admin)

        cls.simple_user = core_factories.UserFactory.create(
            username="user@example.com", groups=("SimpleUsers",),
        )
        admin_factories.MailboxFactory.create(
            address="user", domain=cls.domain, user=cls.simple_user
        )

    def _test_learn(self, mark_as, rcpt, expect_sa_username, domain, user):
        self.set_global_parameter("sa_is_local", True)
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("domain_level_learning", domain)
        self.set_global_parameter("user_level_learning", user)
        with SpamAssassinClient() as sa_client:
            sa_username = sa_client.learn(mark_as, rcpt, b"")
        self.assertEqual(sa_username, expect_sa_username)

    def test_invalid_action(self):
        with self.assertRaises(ValueError):
            with SpamAssassinClient(self.simple_user, "user") as sac:
                sac.learn("invalid", self.simple_user.username, b"")

    def test_manual_learning_disabled(self):
        self.set_global_parameter("manual_learning", False)
        with self.assertRaises(SpamAssassinError):
            with SpamAssassinClient(self.simple_user, "user") as sac:
                sac.learn("spam", self.simple_user.username, b"")

    @override_settings(SA_LOOKUP_PATH=[])
    def test_sa_programs_missing(self):
        """Check a SpamAssassinError is raise if SA programs can't be found."""
        with self.assertRaises(SpamAssassinError):
            SpamAssassinClient(self.simple_user, "user")

    @override_settings(SA_LOOKUP_PATH=[])
    def test_spamc(self):
        self.set_global_parameter("sa_is_local", False)
        self.set_global_parameter("manual_learning", True)
        with self.assertRaises(SpamAssassinError):
            SpamAssassinClient(self.simple_user, "user")

    def test_learn_spam_as_super_admin(self):
        self.set_global_parameter("sa_is_local", False)
        self.set_global_parameter("manual_learning", True)
        with SpamAssassinClient(self.super_admin, "user") as sac:
            sa_username = sac.learn("spam", self.simple_user.username, b"")
        self.assertEqual(sa_username, self.simple_user.username)

    def test_learn_spam_as_domain_admin_global_level(self):
        self.set_global_parameter("sa_is_local", False)
        self.set_global_parameter("manual_learning", True)
        with SpamAssassinClient(self.domain_admin, "global") as sac:
            sa_username = sac.learn("spam", self.simple_user.username, b"")
        self.assertEqual(sa_username, "amavis")

    def test_learn_spam_as_domain_admin_domain_level(self):
        self.set_global_parameter("sa_is_local", False)
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("domain_level_learning", True)
        with SpamAssassinClient(self.domain_admin, "domain") as sac:
            sa_username = sac.learn("spam", self.simple_user.username, b"")
        self.assertEqual(sa_username, self.domain.name)

    def test_learn_spam_as_domain_admin(self):
        self.set_global_parameter("sa_is_local", False)
        self.set_global_parameter("manual_learning", True)
        with SpamAssassinClient(self.domain_admin, "user") as sac:
            sa_username = sac.learn("spam", self.simple_user.username, b"")
        self.assertEqual(sa_username, self.simple_user.username)
