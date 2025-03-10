# Generated by Django 4.2.18 on 2025-02-24 12:33

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_alter_crawlstate_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='crawlstate',
            name='last_polled_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='crawlstate',
            name='source',
            field=models.CharField(choices=[('UI', 'User Interface'), ('API', 'API')], default='API', max_length=30),
        ),
    ]
