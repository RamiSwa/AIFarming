# Generated by Django 5.0.11 on 2025-02-20 13:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monetization', '0002_reportrequest'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reportrequest',
            name='soil_type',
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='latitude',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='longitude',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='moisture',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='nitrogen',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='original_location',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='ph_level',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='phosphorus',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='potassium',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='soil_temp_0_to_7cm',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportrequest',
            name='soil_temp_7_to_28cm',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
