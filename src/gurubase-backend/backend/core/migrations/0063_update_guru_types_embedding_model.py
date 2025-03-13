from django.db import migrations

def update_guru_types(apps, schema_editor):
    GuruType = apps.get_model('core', 'GuruType')
    Settings = apps.get_model('core', 'Settings')

    # Get default embedding model from settings
    settings_obj = Settings.objects.first()
    if not settings_obj:
        return

    # Update all GuruTypes by saving them
    for guru_type in GuruType.objects.all():
        guru_type.save()  # This will trigger the save method which updates the embedding model

def reverse_func(apps, schema_editor):
    # No need for reverse migration as this is just updating existing records
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0062_settings_default_embedding_model_and_more'),  # Replace with your previous migration
    ]

    operations = [
        migrations.RunPython(update_guru_types, reverse_func),
    ] 