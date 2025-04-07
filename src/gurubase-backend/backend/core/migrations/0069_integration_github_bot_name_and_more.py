# Generated by Django 4.2.18 on 2025-04-03 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0068_alter_integration_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='integration',
            name='github_bot_name',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='integration',
            name='github_client_id',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='integration',
            name='github_private_key',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='integration',
            name='github_secret',
            field=models.TextField(blank=True, null=True),
        ),
    ]
