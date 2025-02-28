from django.db import migrations

def set_github_repo_count_limit(apps, schema_editor):
    GuruType = apps.get_model('core', 'GuruType')
    GuruType.objects.all().update(github_repo_count_limit=1)

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_alter_gurutype_github_repos'),
    ]

    operations = [
        migrations.RunPython(set_github_repo_count_limit, reverse_code=migrations.RunPython.noop),
    ] 