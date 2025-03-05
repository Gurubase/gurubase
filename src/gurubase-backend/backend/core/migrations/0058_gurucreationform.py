# Generated by Django 4.2.18 on 2025-03-05 13:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_widgetid_is_wildcard'),
    ]

    operations = [
        migrations.CreateModel(
            name='GuruCreationForm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('github_repo', models.URLField(max_length=2000)),
                ('docs_url', models.URLField(max_length=2000)),
                ('use_case', models.TextField(blank=True, null=True)),
                ('notified', models.BooleanField(default=False)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-date_created'],
            },
        ),
    ]
