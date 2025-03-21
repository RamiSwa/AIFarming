# Generated by Django 5.0.11 on 2025-02-06 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('soil', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='soildata',
            options={'ordering': ['-time']},
        ),
        migrations.AddField(
            model_name='soildata',
            name='last_updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='soildata',
            name='location',
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='soildata',
            name='time',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AddIndex(
            model_name='soildata',
            index=models.Index(fields=['time'], name='soil_soilda_time_4cbfba_idx'),
        ),
        migrations.AddIndex(
            model_name='soildata',
            index=models.Index(fields=['location'], name='soil_soilda_locatio_a7ed6b_idx'),
        ),
        migrations.AddIndex(
            model_name='soildata',
            index=models.Index(fields=['latitude', 'longitude'], name='soil_soilda_latitud_e906dc_idx'),
        ),
    ]
