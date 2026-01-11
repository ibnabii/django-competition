from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contest", "0001_initial"),
    ]

    operations = [
        # First, add username to Django's state (to match database reality)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="user",
                    name="username",
                    field=models.CharField(max_length=150, unique=True),
                ),
            ],
            database_operations=[
                # Do nothing - field already exists in database
            ],
        ),
        # Then, remove it (Django handles the actual database column drop)
        migrations.RemoveField(
            model_name="user",
            name="username",
        ),
    ]
