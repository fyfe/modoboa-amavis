#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import time

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.sql.subqueries import DeleteQuery

from modoboa.parameters import tools as param_tools
from ...models import Maddr, Msgrcpt, Msgs, Quarantine
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

    def handle(self, *args, **options):
        Amavis().load()
        if options["debug"]:
            import logging
            log = logging.getLogger("django.db.backends")
            log.setLevel(logging.DEBUG)
            log.addHandler(logging.StreamHandler())
        self.verbose = options["verbose"]

        conf = dict(param_tools.get_global_parameters("modoboa_amavis"))

        self.__vprint("Deleting marked messages")
        flags = ["D"]
        if conf["released_msgs_cleanup"]:
            flags += ["R"]
        mail_ids = (
            Msgrcpt.objects
            .filter(rs__in=flags)
            .values_list("mail_id", flat=True)
            .distinct()
        )
        delete_mail_ids(mail_ids)

        self.__vprint(
            "Deleting messages older than %d days" % conf["max_messages_age"]
        )
        limit = int(time.time()) - (conf["max_messages_age"] * 24 * 3600)
        mail_ids = (
            Msgs.objects
            .filter(time_num__lt=limit)
            .values_list("mail_id", flat=True)
            .distinct()
        )
        delete_mail_ids(mail_ids)

        existing_mail_ids = (
            Msgs.objects
            .values_list("mail_id", flat=True)
            .distinct()
        )

        self.__vprint("Deleting unrefrenced msgrcpt objects")
        mail_ids = (
            Msgrcpt.objects
            .exclude(mail_id__in=existing_mail_ids)
            .values_list("mail_id", flat=True)
            .distinct()
        )
        delete_mail_ids(mail_ids)

        self.__vprint("Deleting unrefrenced quarantine objects")
        mail_ids = (
            Quarantine.objects
            .exclude(mail_id__in=existing_mail_ids)
            .values_list("mail_id", flat=True)
            .distinct()
        )
        delete_mail_ids(mail_ids)

        self.__vprint("Deleting unreferenced e-mail addresses")
        (
            Maddr.objects
            .annotate(msgs_count=Count("msgs"), msgrcpt_count=Count("msgrcpt"))
            .filter(msgs_count=0, msgrcpt_count=0)
            .distinct()
            .delete()
        )

        self.__vprint("Done.")


def truncate_queryset(qs):
    """
    Deletes all records matched by queryset using

        DELETE from table WHERE <condition>

    query without fetching PK values for all items in original queryset.
    """

    delete_query = qs.query.clone(DeleteQuery)
    delete_query.get_compiler(qs.db).execute_sql(None)


def delete_mail_ids(mail_ids):
    truncate_queryset(Quarantine.objects.filter(mail_id__in=mail_ids))
    truncate_queryset(Msgrcpt.objects.filter(mail_id__in=mail_ids))
    truncate_queryset(Msgs.objects.filter(mail_id__in=mail_ids))
