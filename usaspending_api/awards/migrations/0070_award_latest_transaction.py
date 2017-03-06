# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-03-06 19:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0069_auto_20170306_1727'),
    ]

    operations = [
        migrations.AddField(
            model_name='award',
            name='latest_transaction',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='latest_transaction', to='awards.Transaction'),
        ),
    ]
