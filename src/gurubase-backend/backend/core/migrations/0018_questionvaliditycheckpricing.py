# Generated by Django 4.2.13 on 2025-01-13 14:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_merge_20250113_1453'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionValidityCheckPricing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=1500)),
                ('cost_dollars', models.FloatField(blank=True, default=0, null=True)),
                ('completion_tokens', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('prompt_tokens', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('cached_prompt_tokens', models.PositiveIntegerField(blank=True, default=0, null=True)),
            ],
        ),
    ]
