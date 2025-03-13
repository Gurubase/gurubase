# Generated by Django 4.2.18 on 2025-03-12 19:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0060_alter_crawlstate_guru_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='gurutype',
            name='code_embedding_model',
            field=models.CharField(choices=[('GEMINI_EMBEDDING_001', 'Gemini - embedding-001'), ('GEMINI_TEXT_EMBEDDING_004', 'Gemini - text-embedding-004'), ('OPENAI_TEXT_EMBEDDING_3_SMALL', 'OpenAI - text-embedding-3-small'), ('OPENAI_TEXT_EMBEDDING_3_LARGE', 'OpenAI - text-embedding-3-large'), ('OPENAI_TEXT_EMBEDDING_ADA_002', 'OpenAI - text-embedding-ada-002')], default='OPENAI_TEXT_EMBEDDING_3_SMALL', max_length=100),
        ),
        migrations.AddField(
            model_name='gurutype',
            name='text_embedding_model',
            field=models.CharField(choices=[('GEMINI_EMBEDDING_001', 'Gemini - embedding-001'), ('GEMINI_TEXT_EMBEDDING_004', 'Gemini - text-embedding-004'), ('OPENAI_TEXT_EMBEDDING_3_SMALL', 'OpenAI - text-embedding-3-small'), ('OPENAI_TEXT_EMBEDDING_3_LARGE', 'OpenAI - text-embedding-3-large'), ('OPENAI_TEXT_EMBEDDING_ADA_002', 'OpenAI - text-embedding-ada-002')], default='OPENAI_TEXT_EMBEDDING_3_SMALL', max_length=100),
        ),
    ]
