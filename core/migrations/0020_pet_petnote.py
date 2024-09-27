# Generated by Django 5.1.1 on 2024-09-27 20:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_staffunavailability_is_active'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pet_name', models.CharField(max_length=25)),
                ('pet_types', models.JSONField(default=list)),
                ('pet_bio', models.TextField(blank=True)),
                ('is_public', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('customers', models.ManyToManyField(related_name='pets', to='core.customerprofile')),
            ],
        ),
        migrations.CreateModel(
            name='PetNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.TextField()),
                ('is_private', models.BooleanField(default=False)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pet_notes', to='core.staffprofile')),
                ('pet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='core.pet')),
            ],
        ),
    ]
