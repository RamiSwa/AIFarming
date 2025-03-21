# Generated by Django 5.0.11 on 2025-02-14 00:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0005_alter_recommendation_ai_model_version'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recommendation',
            name='ai_model_version',
            field=models.CharField(help_text='AI model version used for this recommendation.', max_length=50),
        ),
    ]
