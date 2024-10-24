# Generated by Django 5.1.1 on 2024-10-07 15:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_booking_recurrence'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlacklistedPet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(blank=True, null=True)),
                ('date_blacklisted', models.DateTimeField(auto_now_add=True)),
                ('daycare', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.daycare')),
                ('pet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.pet')),
            ],
        ),
    ]
