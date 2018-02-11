# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

import mock

from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes

from rest_framework import status

from modoboa.admin import factories as admin_factories
from modoboa.core import factories as core_factories, models as core_models
from modoboa.lib.tests import ModoAPITestCase
from modoboa_amavis import factories as amavis_factories


class MultiDBMixIn(object):
    multi_db = True


class PageNumberPaginationTestCase(MultiDBMixIn, ModoAPITestCase):

    """Tests for PageNumberPagination."""

    @classmethod
    def setUpTestData(cls):  # noqa: N802
        """Create initial test data that's shared by all tests."""
        super(PageNumberPaginationTestCase, cls).setUpTestData()
        cls.domain = admin_factories.DomainFactory(name="example.com")
        cls.user = core_factories.UserFactory.create(
            username="user@example.com", groups=("SimpleUsers",),
        )
        admin_factories.MailboxFactory.create(
            address="user", domain=cls.domain, user=cls.user
        )
        for i_ in range(51):  # NOQA:B007
            amavis_factories.create_spam(cls.user.username)
        cls.urls = {
            "list": reverse("api:quarantine-list"),
        }

    def setUp(self):  # noqa: N802
        """Create initial test data that's modified by tests."""
        super(PageNumberPaginationTestCase, self).setUp()
        # 40 is the default set in forms.py#UserSettings
        self.user.parameters.set_value(
            "messages_per_page", 40, app="modoboa_amavis"
        )
        self.client.force_authenticate(user=self.user)

    def test_list(self):
        """Test pagination values on list view."""
        response = self.client.get(self.urls["list"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 51)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])
        # 40 is the default set in forms.py#UserSettings
        self.assertEqual(len(response.data["results"]), 40)

    def test_list_page_size_user_setting_invalid(self):
        """Use default page size when user setting is invalid."""
        self.user.parameters.set_value(
            "messages_per_page", "foobar", app="modoboa_amavis"
        )
        response = self.client.get(self.urls["list"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]),
            # NOTE: @fyfe 25 == (max_page_size / 2)
            25
        )


@override_settings(SA_LOOKUP_PATH=(os.path.dirname(__file__), ))
class QuarantineViewSetTestCase(MultiDBMixIn, ModoAPITestCase):

    """Tests for QuarantineViewSet."""

    @classmethod
    def setUpTestData(cls):  # noqa: N802
        """Create initial test data that's shared by all tests."""
        super(QuarantineViewSetTestCase, cls).setUpTestData()
        cls.super_admin = core_models.User.objects.get(username="admin")
        cls.domain1 = admin_factories.DomainFactory(name="example.com")
        cls.domain2 = admin_factories.DomainFactory(name="example.net")

        cls.domain_admin = core_factories.UserFactory.create(
            username="admin@example.com", groups=("DomainAdmins",),
        )
        admin_factories.MailboxFactory.create(
            address="admin", domain=cls.domain1, user=cls.domain_admin
        )
        cls.domain1.add_admin(cls.domain_admin)

        cls.simple_user = core_factories.UserFactory.create(
            username="user@example.com", groups=("SimpleUsers",),
        )
        admin_factories.MailboxFactory.create(
            address="user", domain=cls.domain1, user=cls.simple_user
        )

        cls.reseller = core_factories.UserFactory.create(
            username="reseller@example.net", groups=("Resellers",),
        )
        admin_factories.MailboxFactory.create(
            address="reseller", domain=cls.domain2, user=cls.reseller
        )

        cls.spam = {
            "admin_spam":
                amavis_factories.create_spam(cls.domain_admin.username),
            "user_pending":
                amavis_factories.create_spam(cls.simple_user.username, rs="p"),
            "user_deleted":
                amavis_factories.create_spam(cls.simple_user.username, rs="D"),
            "user_viewed":
                amavis_factories.create_spam(cls.simple_user.username, rs="V"),
            "user_released":
                amavis_factories.create_spam(cls.simple_user.username, rs="R"),
            "user_marked_as_spam":
                amavis_factories.create_spam(cls.simple_user.username, rs="S"),
            "user_marked_as_ham":
                amavis_factories.create_spam(cls.simple_user.username, rs="H"),
            "other_user_spam":
                amavis_factories.create_spam(cls.reseller.username),
        }

        cls.urls = {
            "list": reverse("api:quarantine-list"),
            "requests": reverse("api:quarantine-requests"),
        }

    def setUp(self):  # noqa: N802
        """Create initial test data that's modified by tests."""
        super(QuarantineViewSetTestCase, self).setUp()
        self.spam["user_spam"] = amavis_factories.create_spam(
            self.simple_user.username
        )

    def test_list_requests(self):
        self.client.force_authenticate(user=self.simple_user)
        response = self.client.get(self.urls["requests"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_list_as_super_admin(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(self.urls["list"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 8)

    def test_list_as_domain_admin(self):
        self.client.force_authenticate(user=self.domain_admin)
        response = self.client.get(self.urls["list"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 7)

    def test_list_as_reseller(self):
        self.client.force_authenticate(user=self.reseller)
        response = self.client.get(self.urls["list"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_list_as_simple_user(self):
        self.client.force_authenticate(user=self.simple_user)
        response = self.client.get(self.urls["list"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 6)

    def test_detail(self):
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse("api:quarantine-detail", kwargs={"mail_id": mail_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["mail_id"], mail_id)

    def test_mark_as_spam(self):
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("user_level_learning", True)
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse(
            "api:quarantine-mark-as-spam", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url, {"recipient_db": "user"})
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.spam["user_spam"].rs, "S")

    def test_mark_as_spam_invalid_recipient_db(self):
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("user_level_learning", True)
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse(
            "api:quarantine-mark-as-spam", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url, {"recipient_db": "invalid"})
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotEqual(self.spam["user_spam"].rs, "S")

    def test_mark_as_spam_no_recipient_db(self):
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("user_level_learning", True)
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse(
            "api:quarantine-mark-as-spam", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url)
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotEqual(self.spam["user_spam"].rs, "S")

    @override_settings(SA_LOOKUP_PATH=[])
    def test_mark_as_spam_error(self):
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("user_level_learning", True)
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse(
            "api:quarantine-mark-as-spam", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url, {"recipient_db": "user"})
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(
            response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertNotEqual(self.spam["user_spam"].rs, "S")

    def test_mark_as_ham(self):
        self.set_global_parameter("manual_learning", True)
        self.set_global_parameter("user_level_learning", True)
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse(
            "api:quarantine-mark-as-ham", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url, {"recipient_db": "user"})
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.spam["user_spam"].rs, "H")

    def test_release(self):  # user_can_release
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse(
            "api:quarantine-release", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url)
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.spam["user_spam"].rs, "p")

    @mock.patch("socket.socket")
    def test_release_with_user_can_release(self, mock_socket):
        mail_id = self.spam["user_spam"].mail_id
        mock_socket.return_value.recv.return_value = force_bytes(
            r"250 2.5.0 Ok,%20id={},%20continue%20delivery\r\n".format(mail_id)
        )
        self.set_global_parameter("user_can_release", True)
        self.client.force_authenticate(user=self.simple_user)
        url = reverse(
            "api:quarantine-release", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url)
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.spam["user_spam"].rs, "R")

    @mock.patch("socket.socket")
    def test_release_error(self, mock_socket):
        mail_id = self.spam["user_spam"].mail_id
        mock_socket.return_value.recv.return_value = force_bytes(
            r"451 4.5.0 Error%20in%20processing,%20id={}\r\n".format(mail_id)
        )
        self.set_global_parameter("user_can_release", True)
        self.client.force_authenticate(user=self.simple_user)
        url = reverse(
            "api:quarantine-release", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url)
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertNotEqual(self.spam["user_spam"].rs, "R")

    @mock.patch("socket.socket")
    def test_bulk_release(self, mock_socket):
        mail_id = self.spam["user_spam"].mail_id
        mock_socket.return_value.recv.return_value = force_bytes(
            r"250 2.5.0 Ok,%20id={},%20continue%20delivery\r\n".format(mail_id)
        )
        self.set_global_parameter("user_can_release", True)
        self.client.force_authenticate(user=self.simple_user)
        url = reverse("api:quarantine-bulk-release")
        response = self.client.post(
            url, {"mail_id": [mail_id]}, format="json"
        )
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.spam["user_spam"].rs, "R")

    @mock.patch("socket.socket")
    def test_bulk_release_error(self, mock_socket):
        mail_id = self.spam["user_spam"].mail_id
        mock_socket.return_value.recv.return_value = force_bytes(
            r"451 4.5.0 Error%20in%20processing,%20id={}\r\n".format(mail_id)
        )
        self.set_global_parameter("user_can_release", True)
        self.client.force_authenticate(user=self.simple_user)
        url = reverse("api:quarantine-bulk-release")
        response = self.client.post(
            url, {"mail_id": [mail_id]}, format="json"
        )
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertNotEqual(self.spam["user_spam"].rs, "R")
        self.assertIn("errors", response.data)

    def test_bulk_release_no_mail_id(self):
        self.client.force_authenticate(user=self.simple_user)
        url = reverse("api:quarantine-bulk-release")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_delete(self):
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse(
            "api:quarantine-delete", kwargs={"mail_id": mail_id}
        )
        response = self.client.post(url)
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.spam["user_spam"].rs, "D")
        self.assertIn("detail", response.data)
        self.assertIn("mail_id", response.data)

    def test_bulk_delete(self):
        self.client.force_authenticate(user=self.simple_user)
        mail_id = self.spam["user_spam"].mail_id
        url = reverse("api:quarantine-bulk-delete")
        response = self.client.post(
            url, {"mail_id": [mail_id]}, format="json"
        )
        self.spam["user_spam"].refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.spam["user_spam"].rs, "D")
        self.assertIn("detail", response.data)
        self.assertIn("mail_id", response.data)

    def test_bulk_delete_no_mail_id(self):
        self.client.force_authenticate(user=self.simple_user)
        url = reverse("api:quarantine-bulk-delete")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
