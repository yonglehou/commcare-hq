# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_analytics', '0005_girrow'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='girrow',
            unique_together=set([('month', 'domain_name')]),
        ),
    ]
