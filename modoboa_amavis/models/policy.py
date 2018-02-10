# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy

from modoboa_amavis.fields import BinaryCharField


class Policy(models.Model):
    id = models.AutoField(primary_key=True)  # NOQA:A003
    policy_name = models.CharField(max_length=32, blank=True)

    virus_lover = models.CharField(max_length=1, blank=True, null=True)
    spam_lover = models.CharField(max_length=1, blank=True, null=True)
    unchecked_lover = models.CharField(max_length=1, blank=True, null=True)
    banned_files_lover = models.CharField(max_length=1, blank=True, null=True)
    bad_header_lover = models.CharField(max_length=1, blank=True, null=True)

    bypass_virus_checks = models.CharField(
        ugettext_lazy("Virus filter"), default="", null=True,
        choices=(("N", ugettext_lazy("yes")),
                 ("Y", ugettext_lazy("no")),
                 ("", ugettext_lazy("default"))),
        max_length=1,
        help_text=ugettext_lazy(
            "Bypass virus checks or not. Choose 'default' to use global "
            "settings."
        )
    )
    bypass_spam_checks = models.CharField(
        ugettext_lazy("Spam filter"), default="", null=True,
        choices=(("N", ugettext_lazy("yes")),
                 ("Y", ugettext_lazy("no")),
                 ("", ugettext_lazy("default"))),
        max_length=1,
        help_text=ugettext_lazy(
            "Bypass spam checks or not. Choose 'default' to use global "
            "settings."
        )
    )
    bypass_banned_checks = models.CharField(
        ugettext_lazy("Banned filter"), default="", null=True,
        choices=(("N", ugettext_lazy("yes")),
                 ("Y", ugettext_lazy("no")),
                 ("", ugettext_lazy("default"))),
        max_length=1,
        help_text=ugettext_lazy(
            "Bypass banned checks or not. Choose 'default' to use global "
            "settings."
        )
    )
    bypass_header_checks = models.CharField(
        max_length=1, blank=True, null=True)
    virus_quarantine_to = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    spam_quarantine_to = models.CharField(
        max_length=64, blank=True, null=True)
    banned_quarantine_to = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    unchecked_quarantine_to = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    bad_header_quarantine_to = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    clean_quarantine_to = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    archive_quarantine_to = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    spam_tag_level = models.DecimalField(max_digits=7, decimal_places=4)
    spam_tag2_level = models.DecimalField(max_digits=7, decimal_places=4)
    spam_tag3_level = models.DecimalField(max_digits=7, decimal_places=4)
    spam_kill_level = models.DecimalField(max_digits=7, decimal_places=4)
    spam_dsn_cutoff_level = models.DecimalField(max_digits=7, decimal_places=4)
    spam_quarantine_cutoff_level = models.DecimalField(
        max_digits=7, decimal_places=4
    )
    addr_extension_virus = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    addr_extension_spam = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    addr_extension_banned = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    addr_extension_bad_header = models.CharField(
        max_length=64,
        blank=True,
        null=True)
    warnvirusrecip = models.CharField(max_length=1, blank=True, null=True)
    warnbannedrecip = models.CharField(max_length=1, blank=True, null=True)
    warnbadhrecip = models.CharField(max_length=1, blank=True, null=True)
    newvirus_admin = models.CharField(max_length=64, blank=True, null=True)
    virus_admin = models.CharField(max_length=64, blank=True, null=True)
    banned_admin = models.CharField(max_length=64, blank=True, null=True)
    bad_header_admin = models.CharField(max_length=64, blank=True, null=True)
    spam_admin = models.CharField(max_length=64, blank=True, null=True)
    spam_subject_tag = models.CharField(max_length=64, blank=True, null=True)
    spam_subject_tag2 = models.CharField(
        ugettext_lazy("Spam marker"), default=None,
        max_length=64, blank=True, null=True,
        help_text=ugettext_lazy(
            "Modify spam subject using the specified text. "
            "Choose 'default' to use global settings."
        )
    )
    spam_subject_tag3 = models.CharField(max_length=64, blank=True, null=True)
    message_size_limit = models.IntegerField(null=True, blank=True)
    banned_rulenames = models.CharField(max_length=64, blank=True, null=True)
    disclaimer_options = models.CharField(
        max_length=64, blank=True, null=True)
    forward_method = models.CharField(max_length=64, blank=True, null=True)
    sa_userconf = models.CharField(max_length=64, blank=True, null=True)
    sa_username = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        db_table = "policy"
        managed = False


class Users(models.Model):
    id = models.AutoField(primary_key=True)  # NOQA:A003
    priority = models.IntegerField(default=7)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE)
    email = BinaryCharField(unique=True, max_length=255)
    fullname = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "users"
        managed = False


class Mailaddr(models.Model):
    id = models.AutoField(primary_key=True)  # NOQA:A003
    priority = models.IntegerField(default=7)
    email = BinaryCharField(unique=True, max_length=255)

    class Meta:
        db_table = "mailaddr"
        managed = False


class Wblist(models.Model):
    rid = models.ForeignKey(
        Mailaddr, db_column="rid", related_name="wbl_recipient",
        on_delete=models.CASCADE
    )
    sid = models.ForeignKey(
        Mailaddr, db_column="sid", related_name="wbl_sender",
        on_delete=models.CASCADE
    )
    wb = models.CharField(max_length=10)

    class Meta:
        db_table = "wblist"
        managed = False
        unique_together = [("rid", "sid")]
