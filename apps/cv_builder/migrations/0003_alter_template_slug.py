from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cv_builder", "0002_rename_template_design_to_slug_field"),
    ]

    operations = [
        migrations.AlterField(
            model_name="template",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
    ]