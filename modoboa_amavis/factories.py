# -*- coding: utf-8 -*-

"""Amavis factories."""

from __future__ import unicode_literals

import datetime
import io
import os
import time

import factory

from . import lib, models
from .utils import smart_bytes

SAMPLES_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "tests", "sample_messages"))
SAMPLE_MESSAGE = None


class MaddrFactory(factory.DjangoModelFactory):
    """Factory for Maddr."""

    class Meta:
        model = models.Maddr
        django_get_or_create = ("email", )

    email = factory.Sequence(lambda n: "user_{}@domain.test".format(n))
    domain = factory.LazyAttribute(
        lambda o:
            ".".join(lib.split_address(o.email)[1].split(".")[::-1])
    )


class MsgsFactory(factory.DjangoModelFactory):
    """Factory for Mailaddr."""

    class Meta:
        model = models.Msgs

    mail_id = factory.Sequence(lambda n: "mailid{}".format(n))
    secret_id = factory.Sequence(lambda n: "id{}".format(n))
    sid = factory.SubFactory(MaddrFactory)
    client_addr = "127.0.0.1"
    originating = "Y"
    dsn_sent = "N"
    from_addr = factory.LazyAttribute(lambda o: o.sid.email)
    subject = factory.Sequence(lambda n: "Test message {}".format(n))
    time_num = factory.LazyAttribute(lambda o: int(time.time()))
    time_iso = factory.LazyAttribute(
        lambda o: datetime.datetime.fromtimestamp(o.time_num).isoformat())
    size = 100


class MsgrcptFactory(factory.DjangoModelFactory):
    """Factory for Msgrcpt."""

    class Meta:
        model = models.Msgrcpt

    is_local = "Y"
    mail = factory.SubFactory(MsgsFactory)
    rid = factory.SubFactory(MaddrFactory)


class QuarantineFactory(factory.DjangoModelFactory):
    """Factory for Quarantine."""

    class Meta:
        model = models.Quarantine

    mail = factory.SubFactory(MsgsFactory)


def create_quarantined_msg(rcpt, sender, rs, body, **kwargs):
    """Create a quarantined msg."""
    msg = MsgsFactory(
        sid=MaddrFactory(email=sender),
    )
    msgrcpt = MsgrcptFactory(
        rs=rs,
        rid=MaddrFactory(email=rcpt),
        mail=msg,
        **kwargs
    )
    QuarantineFactory(
        mail=msgrcpt.mail,
        mail_text=body
    )
    return msgrcpt


def create_spam(rcpt, sender="spam@evil.corp", rs=" "):
    """Create a spam."""
    body = _get_sample_message()
    return create_quarantined_msg(
        rcpt, sender, rs, body, bspam_level=999.0, content="S")


def create_virus(rcpt, sender="virus@evil.corp", rs=" "):
    """Create a virus."""
    body = _get_sample_message()
    return create_quarantined_msg(rcpt, sender, rs, body, content="V")


def _get_sample_message():
    global SAMPLE_MESSAGE
    if SAMPLE_MESSAGE is None:
        message_path = os.path.join(SAMPLES_DIR, "quarantined-input.txt")
        assert os.path.isfile(message_path), "%s does not exist." % message_path

        with io.open(message_path, "rb") as fp:
            SAMPLE_MESSAGE = smart_bytes(fp.read())

    return SAMPLE_MESSAGE
