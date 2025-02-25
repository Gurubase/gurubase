from django.db import migrations, models
from urllib.parse import urlparse

def populate_domain_field(apps, schema_editor):
    WidgetId = apps.get_model('core', 'WidgetId')
    for widget in WidgetId.objects.all():
        parsed_url = urlparse(widget.domain_url)
        widget.domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        widget.save()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_outofcontextquestion_core_outofc_guru_ty_a23c4d_idx_and_more'),  # Replace with the previous migration
    ]

    operations = [
        # Add the domain field
        migrations.AddField(
            model_name='widgetid',
            name='domain',
            field=models.URLField(max_length=2000, default=''),
            preserve_default=False,
        ),
        # Populate the domain field for existing records
        migrations.RunPython(populate_domain_field, reverse_code=migrations.RunPython.noop),
    ] 