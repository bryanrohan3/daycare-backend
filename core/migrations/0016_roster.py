# Generated by Django 5.1.1 on 2024-09-13 03:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_daycare_pet_types'),
    ]

    operations = [
        migrations.CreateModel(
            name='Roster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_shift', models.DateTimeField()),
                ('end_shift', models.DateTimeField()),
                ('shift_day', models.DateField()),
                ('daycare', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roster', to='core.daycare')),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roster', to='core.staffprofile')),
            ],
        ),
    ]
