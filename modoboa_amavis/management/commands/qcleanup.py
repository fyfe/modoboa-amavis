#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils.encoding import force_bytes

from modoboa.parameters import tools as param_tools
from ...models import Maddr, Msgrcpt, Msgs
from ...modo_extension import Amavis


class Command(BaseCommand):
    args = ""
    help = "Amavis quarantine cleanup"  # NOQA:A003

    def add_arguments(self, parser):
        """Add extra arguments to command line."""
        parser.add_argument(
            "--debug", action="store_true", default=False,
            help="Activate debug output")
        parser.add_argument(
            "--verbose", action="store_true", default=False,
            help="Display informational messages")

    def __vprint(self, msg):
        if not self.verbose:
            return
        print(msg)

    @transaction.atomic
    def handle(self, *args, **options):
        Amavis().load()
        if options["debug"]:
            import logging
            log = logging.getLogger("django.db.backends")
            log.setLevel(logging.DEBUG)
            log.addHandler(logging.StreamHandler())
        self.verbose = options["verbose"]

        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))

        flags = ["D"]
        if conf["released_msgs_cleanup"]:
            flags += ["R"]

        self.__vprint("Deleting marked messages...")
        mail_ids = (
            force_bytes(mail_id)
            for mail_id in (
                Msgrcpt.objects
                .filter(rs__in=flags)
                .values_list("mail_id", flat=True)
                .distinct()
            )
        )
        total_deleted, deleted_by_model_ = (
            Msgs.objects.filter(mail_id__in=mail_ids).delete()
        )
        self.__vprint("%d marked messages deleted" % total_deleted)

        self.__vprint(
            "Deleting messages older than {} days...".format(
                conf["max_messages_age"]))
        limit = int(time.time()) - (conf["max_messages_age"] * 24 * 3600)
        mail_ids = (
            force_bytes(mail_id)
            for mail_id in (
                Msgs.objects
                .filter(time_num__lt=limit)
                .values_list("mail_id", flat=True)
                .distinct()
            )
        )
        total_deleted, deleted_by_model_ = (
            Msgs.objects.filter(mail_id__in=mail_ids).delete()
        )
        self.__vprint(
            "%d messages older than %s days deleted" %
            (total_deleted, conf["max_messages_age"])
        )

        self.__vprint("Deleting unreferenced e-mail addresses...")
        total_deleted, deleted_by_model_ = (
            Maddr.objects
            .annotate(msgs_count=Count("msgs"), msgrcpt_count=Count("msgrcpt"))
            .filter(msgs_count=0, msgrcpt_count=0)
            .delete()
        )
        self.__vprint(
            "%d unreferenced e-mail addresses deleted" % total_deleted
        )

        self.__vprint("Done.")
