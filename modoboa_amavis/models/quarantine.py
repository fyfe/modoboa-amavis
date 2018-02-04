# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import models


class Maddr(models.Model):
    partition_tag = models.IntegerField(default=0)
    id = models.BigIntegerField(primary_key=True)  # NOQA:A003
    email = models.CharField(max_length=255)
    domain = models.CharField(max_length=255)

    class Meta:
        db_table = "maddr"
        unique_together = [("partition_tag", "email")]
        managed = False


class Msgs(models.Model):
    partition_tag = models.IntegerField(default=0)
    mail_id = models.CharField(max_length=12, primary_key=True)
    secret_id = models.BinaryField()
    am_id = models.CharField(max_length=60)
    time_num = models.IntegerField()
    time_iso = models.CharField(max_length=48)
    sid = models.ForeignKey(Maddr, db_column="sid", on_delete=models.CASCADE)
    policy = models.CharField(max_length=765, blank=True)
    client_addr = models.CharField(max_length=765, blank=True)
    size = models.IntegerField()
    originating = models.CharField(max_length=3)
    content = models.CharField(max_length=1, blank=True)
    quar_type = models.CharField(max_length=1, blank=True)
    quar_loc = models.CharField(max_length=255, blank=True)
    dsn_sent = models.CharField(max_length=3, blank=True)
    spam_level = models.FloatField(null=True, blank=True)
    message_id = models.CharField(max_length=765, blank=True)
    from_addr = models.CharField(max_length=765, blank=True)
    subject = models.CharField(max_length=765, blank=True)
    host = models.CharField(max_length=765)

    class Meta:
        db_table = "msgs"
        managed = False
        unique_together = ("partition_tag", "mail_id")


class Msgrcpt(models.Model):
    partition_tag = models.IntegerField(default=0)
    mail = models.ForeignKey(Msgs, primary_key=True, on_delete=models.CASCADE)
    rid = models.ForeignKey(Maddr, db_column="rid", on_delete=models.CASCADE)
    rseqnum = models.IntegerField(default=0)
    is_local = models.CharField(max_length=3)
    content = models.CharField(max_length=3)
    ds = models.CharField(max_length=3)
    rs = models.CharField(max_length=3)
    bl = models.CharField(max_length=3, blank=True)
    wl = models.CharField(max_length=3, blank=True)
    bspam_level = models.FloatField(null=True, blank=True)
    smtp_resp = models.CharField(max_length=765, blank=True)

    class Meta:
        db_table = "msgrcpt"
        managed = False
        unique_together = ("partition_tag", "mail", "rseqnum")


class Quarantine(models.Model):
    partition_tag = models.IntegerField(default=0)
    mail = models.ForeignKey(Msgs, primary_key=True, on_delete=models.CASCADE)
    chunk_ind = models.IntegerField()
    mail_text = models.BinaryField()

    class Meta:
        db_table = "quarantine"
        managed = False
        ordering = ["-mail__time_num"]
        unique_together = ("partition_tag", "mail", "chunk_ind")
