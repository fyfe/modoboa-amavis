# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Maddr',
            fields=[
                ('partition_tag', models.IntegerField(default=0)),
                ('id', models.BigIntegerField(serialize=False, primary_key=True)),
                ('email', models.CharField(unique=True, max_length=255)),
                ('domain', models.CharField(max_length=765)),
            ],
            options={
                'db_table': 'maddr',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Msgs',
            fields=[
                ('partition_tag', models.IntegerField(default=0)),
                ('mail_id', models.CharField(max_length=12, serialize=False, primary_key=True)),
                ('secret_id', models.CharField(max_length=12, blank=True)),
                ('am_id', models.CharField(max_length=60)),
                ('time_num', models.IntegerField()),
                ('time_iso', models.CharField(max_length=48)),
                ('policy', models.CharField(max_length=765, blank=True)),
                ('client_addr', models.CharField(max_length=765, blank=True)),
                ('size', models.IntegerField()),
                ('originating', models.CharField(max_length=3)),
                ('content', models.CharField(max_length=1, blank=True)),
                ('quar_type', models.CharField(max_length=1, blank=True)),
                ('quar_loc', models.CharField(max_length=255, blank=True)),
                ('dsn_sent', models.CharField(max_length=3, blank=True)),
                ('spam_level', models.FloatField(null=True, blank=True)),
                ('message_id', models.CharField(max_length=765, blank=True)),
                ('from_addr', models.CharField(max_length=765, blank=True)),
                ('subject', models.CharField(max_length=765, blank=True)),
                ('host', models.CharField(max_length=765)),
            ],
            options={
                'db_table': 'msgs',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Msgrcpt',
            fields=[
                ('partition_tag', models.IntegerField(default=0)),
                ('mail', models.ForeignKey(primary_key=True, serialize=False, to='modoboa_amavis.Msgs', on_delete=models.CASCADE)),
                ('rseqnum', models.IntegerField(default=0)),
                ('is_local', models.CharField(max_length=3)),
                ('content', models.CharField(max_length=3)),
                ('ds', models.CharField(max_length=3)),
                ('rs', models.CharField(max_length=3)),
                ('bl', models.CharField(max_length=3, blank=True)),
                ('wl', models.CharField(max_length=3, blank=True)),
                ('bspam_level', models.FloatField(null=True, blank=True)),
                ('smtp_resp', models.CharField(max_length=765, blank=True)),
            ],
            options={
                'db_table': 'msgrcpt',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Quarantine',
            fields=[
                ('partition_tag', models.IntegerField(default=0)),
                ('mail', models.ForeignKey(primary_key=True, serialize=False, to='modoboa_amavis.Msgs', on_delete=models.CASCADE)),
                ('chunk_ind', models.IntegerField()),
                ('mail_text', models.TextField()),
            ],
            options={
                'ordering': ['-mail__time_num'],
                'db_table': 'quarantine',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Policy',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('policy_name', models.CharField(blank=True, max_length=32)),
                ('virus_lover', models.CharField(blank=True, choices=[('Y', 'yes'), ('N', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('spam_lover', models.CharField(blank=True, choices=[('Y', 'yes'), ('N', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('unchecked_lover', models.CharField(blank=True, choices=[('Y', 'yes'), ('N', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('banned_files_lover', models.CharField(blank=True, choices=[('Y', 'yes'), ('N', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('bad_header_lover', models.CharField(blank=True, choices=[('Y', 'yes'), ('N', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('bypass_virus_checks', models.CharField(blank=True, choices=[('N', 'yes'), ('Y', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('bypass_spam_checks', models.CharField(blank=True, choices=[('N', 'yes'), ('Y', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('bypass_banned_checks', models.CharField(blank=True, choices=[('N', 'yes'), ('Y', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('bypass_header_checks', models.CharField(blank=True, choices=[('N', 'yes'), ('Y', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('virus_quarantine_to', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('spam_quarantine_to', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('banned_quarantine_to', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('unchecked_quarantine_to', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('bad_header_quarantine_to', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('clean_quarantine_to', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('archive_quarantine_to', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('spam_tag_level', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=7, null=True)),
                ('spam_tag2_level', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=7, null=True)),
                ('spam_tag3_level', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=7, null=True)),
                ('spam_kill_level', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=7, null=True)),
                ('spam_dsn_cutoff_level', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=7, null=True)),
                ('spam_quarantine_cutoff_level', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=7, null=True)),
                ('addr_extension_virus', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('addr_extension_spam', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('addr_extension_banned', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('addr_extension_bad_header', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('warnvirusrecip', models.CharField(blank=True, choices=[('Y', 'yes'), ('N', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('warnbannedrecip', models.CharField(blank=True, choices=[('Y', 'yes'), ('N', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('warnbadhrecip', models.CharField(blank=True, choices=[('Y', 'yes'), ('N', 'no'), (None, 'default')], default=None, max_length=1, null=True)),
                ('newvirus_admin', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('virus_admin', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('banned_admin', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('bad_header_admin', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('spam_admin', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('spam_subject_tag', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('spam_subject_tag2', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('spam_subject_tag3', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('message_size_limit', models.IntegerField(blank=True, default=None, null=True)),
                ('banned_rulenames', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('disclaimer_options', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('forward_method', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('sa_userconf', models.CharField(blank=True, default=None, max_length=64, null=True)),
                ('sa_username', models.CharField(blank=True, default=None, max_length=64, null=True)),
            ],
            options={
                'db_table': 'policy',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('priority', models.IntegerField(default=7)),
                ('email', models.CharField(max_length=255, unique=True)),
                ('fullname', models.CharField(blank=True, default=None, max_length=255, null=True)),
                ('policy', models.ForeignKey(on_delete=models.CASCADE, to='modoboa_amavis.Policy')),
            ],
            options={
                'db_table': 'users',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='SenderAddress',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('priority', models.IntegerField(default=5)),
                ('email', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'db_table': 'mailaddr',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='BlackWhiteList',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('recipient', models.ForeignKey(db_column='rid', on_delete=models.CASCADE, to='modoboa_amavis.User')),
                ('sender', models.ForeignKey(db_column='sid', on_delete=models.CASCADE, to='modoboa_amavis.SenderAddress')),
                ('action_raw', models.CharField(db_column='wb', max_length=10)),
            ],
            options={
                'db_table': 'wblist',
                'managed': False,
                'unique_together': (('recipient', 'sender'),),
            },
        ),
    ]
