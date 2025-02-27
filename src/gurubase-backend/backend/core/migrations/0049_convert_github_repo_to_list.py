from django.db import migrations, models

def convert_github_repo_to_list(apps, schema_editor):
    GuruType = apps.get_model('core', 'GuruType')
    for guru_type in GuruType.objects.all():
        if guru_type.github_repo:
            guru_type.github_repos = [guru_type.github_repo]
            guru_type.save()

def convert_github_repos_to_single(apps, schema_editor):
    GuruType = apps.get_model('core', 'GuruType')
    for guru_type in GuruType.objects.all():
        if guru_type.github_repos:
            guru_type.github_repo = guru_type.github_repos[0] if guru_type.github_repos else ""
            guru_type.save()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0048_crawlstate_last_polled_at_crawlstate_source'),  # Update this to your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='gurutype',
            name='github_repos',
            field=models.JSONField(default=list, blank=True, null=True),
        ),
        migrations.RunPython(convert_github_repo_to_list, convert_github_repos_to_single),
        migrations.RemoveField(
            model_name='gurutype',
            name='github_repo',
        ),
    ] 