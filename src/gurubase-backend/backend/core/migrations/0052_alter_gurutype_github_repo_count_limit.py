# Generated by Django 4.2.18 on 2025-02-28 11:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_set_github_repo_count_limit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gurutype',
            name='github_repo_count_limit',
            field=models.IntegerField(default=1),
        ),
    ]
