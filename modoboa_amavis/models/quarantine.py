# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf import settings
from django.db import models

from modoboa_amavis.fields import BinaryCharField, BinaryForeignKey


class Maddr(models.Model):
    partition_tag = models.IntegerField(default=0)
    id = models.AutoField(primary_key=True)  # NOQA:A003
    email = BinaryCharField(max_length=255)
    domain = models.CharField(max_length=255)

    class Meta:
        db_table = "maddr"
        unique_together = [("partition_tag", "email")]
        managed = False


class Msgs(models.Model):
    partition_tag = models.IntegerField(default=0)
    mail_id = BinaryCharField(max_length=12, primary_key=True)
    secret_id = BinaryCharField(max_length=12)
    am_id = models.CharField(max_length=20)
    time_num = models.IntegerField()
    time_iso = models.CharField(max_length=16)
    sid = models.ForeignKey(Maddr, db_column="sid", on_delete=models.CASCADE)
    policy = models.CharField(max_length=255, blank=True, default="")
    client_addr = models.CharField(max_length=255, blank=True, default="")
    size = models.IntegerField()
    originating = models.CharField(max_length=1, default=" ")
    content = models.CharField(max_length=1, blank=True)
    quar_type = models.CharField(max_length=1, blank=True)
    quar_loc = models.CharField(max_length=255, blank=True, default="")
    dsn_sent = models.CharField(max_length=1, blank=True)
    spam_level = models.DecimalField(max_digits=7, decimal_places=4)
    message_id = models.CharField(max_length=255, blank=True, default="")
    from_addr = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    host = models.CharField(max_length=255)

    class Meta:
        db_table = "msgs"
        managed = False
        unique_together = ("partition_tag", "mail_id")

    def save(self, *args, **kwargs):
        # time_iso fields are too small in the MySQL schema (16 characters),
        # as a temporary fix set time_iso to an empty string.
        # modoboa_amavis doesn't use time_iso it uses time_num.
        if "mysql" in settings.DATABASES["amavis"]["ENGINE"]:
            self.time_iso = ""

        super(Msgs, self).save(*args, **kwargs)


class Msgrcpt(models.Model):
    partition_tag = models.IntegerField(default=0)
    mail = BinaryForeignKey(Msgs, primary_key=True, on_delete=models.CASCADE)
    rseqnum = models.IntegerField(default=0)
    rid = models.ForeignKey(Maddr, db_column="rid", on_delete=models.CASCADE)
    is_local = models.CharField(max_length=1, default=" ")
    content = models.CharField(max_length=1, default=" ")
    ds = models.CharField(max_length=1)
    rs = models.CharField(max_length=1)
    bl = models.CharField(max_length=1, blank=True, default=" ")
    wl = models.CharField(max_length=1, blank=True, default=" ")
    bspam_level = models.DecimalField(max_digits=7, decimal_places=4)
    smtp_resp = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "msgrcpt"
        managed = False
        ordering = ["-mail__time_num"]
        unique_together = ("partition_tag", "mail", "rseqnum")


class Quarantine(models.Model):
    partition_tag = models.IntegerField(default=0)
    mail = BinaryForeignKey(Msgs, primary_key=True, on_delete=models.CASCADE)
    chunk_ind = models.IntegerField(default=1)
    mail_text = models.BinaryField()

    class Meta:
        db_table = "quarantine"
        managed = False
        ordering = ["-mail__time_num"]
        unique_together = ("partition_tag", "mail", "chunk_ind")
