# Generated by Django 4.2.4 on 2023-10-03 00:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0021_userprofile_preferred_language_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EphiosOIDCClient",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("label", models.CharField(max_length=255)),
                ("client_id", models.CharField(max_length=255)),
                ("client_secret", models.CharField(max_length=255)),
                ("scopes", models.CharField(default="openid profile email", max_length=255)),
                ("auth_endpoint", models.URLField()),
                ("token_endpoint", models.URLField()),
                ("user_endpoint", models.URLField()),
                ("jwks_endpoint", models.URLField(blank=True, null=True)),
            ],
        ),
    ]
