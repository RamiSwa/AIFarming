# Generated by Django 5.0.11 on 2025-02-11 00:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0002_crop_preferred_growing_season'),
        ('weather', '0002_alter_weatherdata_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recommendation',
            name='weather_data',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recommendations', to='weather.weatherdata'),
        ),
    ]
