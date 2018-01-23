# -*- coding: utf-8 -*-

"""Amavis tests."""

# [1] TODO: create a PostgreSQL/MySQL test enviroment
#           smart_bytes() is required because the SQLite database used for
#           testing uses a char field for email not a binary field like
#           real world PostgreSQL/MySQL setups.

from __future__ import unicode_literals

from modoboa.admin import factories as admin_factories
from modoboa.core import factories as core_factories
from modoboa.lib.tests import ModoTestCase

from modoboa_amavis import models
from modoboa_amavis.utils import smart_bytes


class DomainPolicyHandlerTestCase(ModoTestCase):

    """Tests for policy handlers."""

    def setUp(self):  # noqa: N802
        """Create initial test data that's modified by tests."""
        super(DomainPolicyHandlerTestCase, self).setUp()
        self.domain = admin_factories.DomainFactory(name="example.com")

    def test_create_domain(self):
        """Check User and Policy are created for a new domain."""
        name = smart_bytes("@%s" % self.domain.name)
        try:
            user = models.User.objects.get(email=name)
        except models.User.DoesNotExist:
            raise
        else:
            # See ^^^ Note [1] ^^^
            self.assertEqual(smart_bytes(user.email), name)
            self.assertEqual(user.fullname, self.domain.name)
            self.assertEqual(user.priority, models.User.Priority.DOMAIN)
            self.assertIsNot(user.policy, None)
            self.assertIsNot(user.policy.policy_name, self.domain.name[:32])

    def test_rename_domain(self):
        """Check User and Policy are updated when a domain is renamed."""
        self.domain.name = "example.net"
        self.domain.save()
        name = smart_bytes("@%s" % self.domain.name)
        try:
            user = models.User.objects.get(email=name)
        except models.User.DoesNotExist:
            raise
        else:
            # See ^^^ Note [1] ^^^
            self.assertEqual(smart_bytes(user.email), name)
            self.assertEqual(user.fullname, self.domain.name)
            self.assertEqual(user.priority, models.User.Priority.DOMAIN)
            self.assertIsNot(user.policy, None)
            self.assertEqual(user.policy.policy_name, self.domain.name[:32])

    def test_delete_domain(self):
        """Check User is deleted when a domain is deleted."""
        name = smart_bytes("@%s" % self.domain.name)
        # None is user deleting object, used by modoboa for logging.
        self.domain.delete(None)
        with self.assertRaises(models.User.DoesNotExist):
            models.User.objects.get(email=name)


class DomainAliasPolicyHandlerTestCase(ModoTestCase):

    """Tests for policy handlers."""

    @classmethod
    def setUpTestData(cls):  # noqa: N802
        """Create initial test data that's shared by all tests."""
        super(DomainAliasPolicyHandlerTestCase, cls).setUpTestData()
        cls.domain = admin_factories.DomainFactory(name="example.com")

    def setUp(self):  # noqa: N802
        """Create initial test data that's modified by tests."""
        super(DomainAliasPolicyHandlerTestCase, self).setUp()
        self.domain_alias = admin_factories.DomainAliasFactory(
            name="example.org", target=self.domain
        )

    def test_create_domainalias(self):
        """Check User and Policy are created for a new domain alias."""
        name = smart_bytes("@%s" % self.domain_alias.name)
        try:
            alias_user = models.User.objects.get(
                email=name, priority=models.User.Priority.DOMAIN_ALIAS
            )
        except models.User.DoesNotExist:
            raise
        else:
            # check policy for new alias
            # See ^^^ Note [1] ^^^
            self.assertEqual(smart_bytes(alias_user.email), name)
            self.assertEqual(alias_user.fullname, self.domain_alias.name)
            self.assertEqual(
                alias_user.priority, models.User.Priority.DOMAIN_ALIAS
            )
            self.assertIsNot(alias_user.policy, None)
            self.assertEqual(
                alias_user.policy.policy_name,
                self.domain_alias.target.name[:32]
            )

    def test_delete_domainalias(self):
        """Check User is deleted when a domain alias is deleted."""
        name = smart_bytes("@%s" % self.domain_alias.name)
        self.domain_alias.delete()
        with self.assertRaises(models.User.DoesNotExist):
            models.User.objects.get(email=name)


class MailboxPolicyHandlerTestCase(ModoTestCase):

    """Tests for policy handlers."""

    @classmethod
    def setUpTestData(cls):  # noqa: N802
        """Create initial test data that's shared by all tests."""
        super(MailboxPolicyHandlerTestCase, cls).setUpTestData()
        cls.domain = admin_factories.DomainFactory(name="example.com")
        cls.account = core_factories.UserFactory.create(
            username="user@example.com", groups=("SimpleUsers",),
        )

    def setUp(self):  # noqa: N802
        """Create initial test data that's modified by tests."""
        super(MailboxPolicyHandlerTestCase, self).setUp()
        self.mailbox = admin_factories.MailboxFactory.create(
            address="user", domain=self.domain, user=self.account
        )

    def test_create_mailbox(self):
        """Check User and Policy are created for a new mailbox."""
        name = smart_bytes(self.mailbox.full_address)
        try:
            user = models.User.objects.get(email=name)
        except models.User.DoesNotExist:
            raise
        else:
            # See ^^^ Note [1] ^^^
            self.assertEqual(smart_bytes(user.email), name)
            self.assertEqual(user.fullname, self.mailbox.full_address)
            self.assertEqual(user.priority, models.User.Priority.USER)
            self.assertIsNot(user.policy, None)
            self.assertIsNot(
                user.policy.policy_name, self.mailbox.full_address[:32]
            )

    def test_rename_mailbox(self):
        """Check User and Policy are updated when a mailbox is renamed."""
        self.mailbox.address = "user2"
        self.mailbox.save()
        name = smart_bytes(self.mailbox.full_address)
        try:
            user = models.User.objects.get(email=name)
        except models.User.DoesNotExist:
            raise
        else:
            # See ^^^ Note [1] ^^^
            self.assertEqual(smart_bytes(user.email), name)
            self.assertEqual(user.fullname, self.mailbox.full_address)
            self.assertEqual(user.priority, models.User.Priority.USER)
            self.assertIsNot(user.policy, None)
            self.assertIsNot(
                user.policy.policy_name, self.mailbox.full_address[:32]
            )

    def test_delete_mailbox(self):
        """Check User is deleted when a mailbox is deleted."""
        name = smart_bytes(self.mailbox.full_address)
        # None is user deleting object, used by modoboa for logging.
        self.mailbox.delete()
        with self.assertRaises(models.User.DoesNotExist):
            models.User.objects.get(email=name)


class MailboxAliasPolicyHandlerTestCase(ModoTestCase):

    """Tests for policy handlers."""

    @classmethod
    def setUpTestData(cls):  # noqa: N802
        """Create initial test data that's shared by all tests."""
        super(MailboxAliasPolicyHandlerTestCase, cls).setUpTestData()
        cls.domain = admin_factories.DomainFactory(name="example.com")
        cls.account = core_factories.UserFactory.create(
            username="user@example.com", groups=("SimpleUsers",),
        )
        cls.mailbox = admin_factories.MailboxFactory.create(
            address="user", domain=cls.domain, user=cls.account
        )

    def setUp(self):  # noqa: N802
        """Create initial test data that's modified by tests."""
        super(MailboxAliasPolicyHandlerTestCase, self).setUp()
        self.alias = admin_factories.AliasFactory.create(
            address="alias@example.com", domain=self.domain
        )
        self.alias_recipient = admin_factories.AliasRecipientFactory.create(
            address=self.mailbox.full_address,
            alias=self.alias, r_mailbox=self.mailbox
        )

    def test_create_mailboxalias(self):
        """Check User and Policy are created for a new mailbox alias."""
        name = smart_bytes(self.alias.address)
        try:
            alias_user = models.User.objects.get(
                email=name, priority=models.User.Priority.USER_ALIAS
            )
        except models.User.DoesNotExist:
            raise
        else:
            # check policy for new alias
            # See ^^^ Note [1] ^^^
            self.assertEqual(smart_bytes(alias_user.email), name)
            self.assertEqual(alias_user.fullname, self.alias.address)
            self.assertEqual(
                alias_user.priority, models.User.Priority.USER_ALIAS
            )
            self.assertIsNot(alias_user.policy, None)
            self.assertEqual(
                alias_user.policy.policy_name, self.alias_recipient.address[:32]
            )

    def test_delete_mailboxalias(self):
        """Check User is deleted when a mailbox alias is deleted."""
        name = smart_bytes(self.alias.address)
        self.alias.delete()
        with self.assertRaises(models.User.DoesNotExist):
            models.User.objects.get(email=name)
