# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-05-17 14:22
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0028_auto_20180402_1751'),
    ]

    operations = [
        migrations.RunSQL(sql="CREATE INDEX modified_generated_unique_award_id_awards_idx ON awards "
                              "(REPLACE(generated_unique_award_id, '-', ''))",
                          reverse_sql="DROP INDEX modified_generated_unique_award_id_awards_idx"),
        migrations.RunSQL(sql="CREATE INDEX modified_fain_awards_idx ON awards (REPLACE(fain, '-', ''))",
                          reverse_sql="DROP INDEX modified_fain_awards_idx")
    ]