from django.db import migrations, models
import django.db.models.deletion
import core.models

def create_initial_languages(apps, schema_editor):
    Language = apps.get_model('core', 'Language')
    
    # Create initial languages
    languages = {
        'ENGLISH': {'name': 'English', 'iso_code': 'en'},
        'TURKISH': {'name': 'Turkish', 'iso_code': 'tr'},
        'DUTCH': {'name': 'Dutch', 'iso_code': 'nl'}
    }
    
    for code, data in languages.items():
        Language.objects.create(
            code=code,
            name=data['name'],
            iso_code=data['iso_code'],
        )

def reverse_migration(apps, schema_editor):
    Language = apps.get_model('core', 'Language')
    Language.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0087_alter_gurutype_language'),
    ]

    operations = [
        # Create Language model
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True)),
                ('name', models.CharField(max_length=50)),
                ('iso_code', models.CharField(max_length=2, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        
        # Create initial languages
        migrations.RunPython(create_initial_languages, reverse_migration),
    ] 