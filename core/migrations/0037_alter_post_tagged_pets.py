# Generated by Django 5.1.1 on 2024-10-23 08:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_post_like_comment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='tagged_pets',
            field=models.ManyToManyField(related_name='posts', to='core.pet'),
        ),
    ]
