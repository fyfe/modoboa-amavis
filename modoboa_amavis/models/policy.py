# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from base64 import urlsafe_b64decode, urlsafe_b64encode
from enum import IntEnum, unique
from decimal import Context as DecimalContext

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from modoboa.parameters import tools as param_tools

from modoboa_amavis.utils import smart_text


class Policy(models.Model):
    _CHOICES_YES_NO_DEFAULT = (
        ("Y", _("yes")),
        ("N", _("no")),
        (None, _("default")),

    )

    _CHOICES_NO_YES_DEFAULT = (
        ("N", _("yes")),
        ("Y", _("no")),
        (None, _("default")),

    )

    id = models.AutoField(primary_key=True)  # noqa:A003
    policy_name = models.CharField(max_length=32, blank=True)

    virus_lover = models.CharField(
        _("Viruses"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_YES_NO_DEFAULT,
        help_text=_("Allow messages marked containing viruses")
    )
    spam_lover = models.CharField(
        _("Spam"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_YES_NO_DEFAULT,
        help_text=_("Allow messages marked as spam")
    )
    unchecked_lover = models.CharField(
        _("Unchecked messages"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_YES_NO_DEFAULT,
        help_text=_("Allow unchecked messages")
    )
    banned_files_lover = models.CharField(
        _("Banned files"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_YES_NO_DEFAULT,
        help_text=_("Allow messages containing banned files")
    )
    bad_header_lover = models.CharField(
        _("Bad headers"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_YES_NO_DEFAULT,
        help_text=_("Allow messages containing bad headers")
    )

    bypass_virus_checks = models.CharField(
        _("Virus filter"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_NO_YES_DEFAULT,
        help_text=_("Bypass virus checks or not.")
    )
    bypass_spam_checks = models.CharField(
        _("Spam filter"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_NO_YES_DEFAULT,
        help_text=_("Bypass spam checks or not.")
    )
    bypass_banned_checks = models.CharField(
        _("Banned file filter"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_NO_YES_DEFAULT,
        help_text=_("Bypass banned file checks or not.")
    )
    bypass_header_checks = models.CharField(
        _("Header checks filter"),
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_NO_YES_DEFAULT,
        help_text=_("Bypass bad header checks or not.")
    )

    virus_quarantine_to = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    spam_quarantine_to = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    banned_quarantine_to = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    unchecked_quarantine_to = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    bad_header_quarantine_to = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    clean_quarantine_to = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    archive_quarantine_to = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )

    spam_tag_level = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True, default=None
    )
    spam_tag2_level = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True, default=None
    )
    spam_tag3_level = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True, default=None
    )
    spam_kill_level = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True, default=None
    )

    spam_dsn_cutoff_level = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True, default=None
    )
    spam_quarantine_cutoff_level = models.DecimalField(
        max_digits=7, decimal_places=4, null=True, blank=True, default=None
    )

    addr_extension_virus = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    addr_extension_spam = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    addr_extension_banned = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    addr_extension_bad_header = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )

    warnvirusrecip = models.CharField(
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_YES_NO_DEFAULT
    )
    warnbannedrecip = models.CharField(
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_YES_NO_DEFAULT
    )
    warnbadhrecip = models.CharField(
        max_length=1, blank=True, null=True, default=None,
        choices=_CHOICES_YES_NO_DEFAULT
    )

    newvirus_admin = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    virus_admin = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    banned_admin = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    bad_header_admin = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    spam_admin = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    spam_subject_tag = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    spam_subject_tag2 = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    spam_subject_tag3 = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    message_size_limit = models.IntegerField(
        blank=True, null=True, default=None
    )
    banned_rulenames = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    disclaimer_options = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    forward_method = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )

    sa_userconf = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )
    sa_username = models.CharField(
        max_length=64, blank=True, null=True, default=None
    )

    class Meta:
        db_table = "policy"
        managed = False


@python_2_unicode_compatible
class User(models.Model):
    id = models.AutoField(primary_key=True)  # noqa:A003
    priority = models.IntegerField(default=7)
    policy = models.ForeignKey(Policy, on_delete=models.PROTECT)
    email = models.CharField(unique=True, max_length=255)  # bytes field
    fullname = models.CharField(
        max_length=255, blank=True, null=True, default=None
    )

    class Meta:
        db_table = "users"
        managed = False

    @unique
    class Priority(IntEnum):
        CATCHALL = 0
        DOMAIN = 1
        DOMAIN_ALIAS = 3
        USER = 4
        USER_ALIAS = 6
        USER_EXTENSION = 7

    def __str__(self):
        return smart_text(self.email)

    def is_global_policy(self):
        return smart_text(self.email).startswith("@")


@python_2_unicode_compatible
class SenderAddress(models.Model):

    """Sender address used for black/white listing.

    This can be either a full e-mail address or just the domain part."""

    id = models.AutoField(primary_key=True)  # noqa: A003
    priority = models.IntegerField(default=5)
    email = models.CharField(max_length=255, unique=True)  # bytes field

    class Meta:
        db_table = "mailaddr"
        managed = False

    def __str__(self):
        return smart_text(self.email)


class BlackWhiteList(models.Model):

    """Black/white list e-mails based on recipient and sender.

    Two modes are supported:

    - Hard Mode; action is W or Y to white list a sender ,  B or N to black list
      a sender. In hard mode all other ham/spam checks are disabled and an
      e-mail is accepted/rejected based on this action.

    - Soft Mode; action is a +ve or -ve score added to the SpamAssassin score
      to influence wheather a message should be treated as ham or spam.

    See https://amavis.org/amavisd-new-docs.html#wblist
    """

    recipient = models.ForeignKey(
        User, db_column="rid", on_delete=models.CASCADE
    )
    sender = models.ForeignKey(
        SenderAddress, db_column="sid", on_delete=models.CASCADE
    )
    action_raw = models.CharField(db_column="wb", max_length=10)

    _ACTION_VALUES = ("W", "Y", "T", "B", "N", "F", " ")
    _SCORE_DECIMAL_CONTEXT = DecimalContext(prec=5)

    class Meta:
        db_table = "wblist"
        managed = False
        unique_together = [("recipient", "sender")]

    def __init__(self, *args, **kwargs):
        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))
        self._HARD_WB_MODE = bool(conf["hard_wb_mode"] or False)
        super(BlackWhiteList, self).__init__(*args, **kwargs)

    @property
    def id(self):
        """Auto generated unique id to identify this entry in web requests."""
        id_ = b"%s|%s" % (self.recipient.email, self.sender.email)
        return urlsafe_b64encode(id_)

    @classmethod
    def id_to_email(cls, id_):
        """Decode an id to recipient, sender email address."""
        id_ = smart_text(urlsafe_b64decode(id_))
        return id_.split("|", 1)

    @property
    def action(self):
        """Action to take when a message is sent to recipient from sender.

        - Hard Mode; 'W' for white list, 'B' for blacklist and None for neutral.

        - Soft Mode; +ve or -ve Decimal() score.
        """
        if self._HARD_WB_MODE:
            value = self.action_raw.upper()
            if value not in self._ACTION_VALUES:
                raise ValueError(_("Hard black/white listing enabled, value "
                                   "(%s) should be one of %s")
                                 % (value, ", ".join(self._ACTION_VALUES)))
            elif value in ["W", "B", None]:
                pass
            elif value in ["Y", "T"]:  # normalise Y(es) or T(rue) == W
                value = "W"
            elif value in ["N", "F"]:  # normalise N(o) or F(alse) == B
                value = "B"
            elif value == " ":  # normalise ' ' == None
                value = None
            else:
                # amavis treats all other values as white list.
                value = "W"
        else:
            try:
                value = self._SCORE_DECIMAL_CONTEXT.create_decimal(
                    self.action_raw)
            except ValueError:
                raise ValueError(_("Soft white/black listing enabled, value "
                                   "(%s) should be a decimal number.")
                                 % value)
        return value

    @action.setter
    def action(self, value):
        if self._HARD_WB_MODE:
            value = value.upper()
            if value not in self._ACTION_VALUES:
                raise ValueError(_("Hard black/white listing enabled, value "
                                   "(%s) should be one of %s")
                                 % (value, ", ".join(self._ACTION_VALUES)))
        else:
            try:
                value = self._SCORE_DECIMAL_CONTEXT.create_decimal(value)
            except ValueError:
                raise ValueError(_("Soft white/black listing enabled, value "
                                   "(%s) should be a decimal number.")
                                 % value)

        self.action_raw = value
