# Generated by Django 5.0.11 on 2025-02-14 00:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0003_alter_recommendation_weather_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='recommendation',
            name='alerts',
            field=models.JSONField(blank=True, default=list, help_text='Important alerts related to the recommendation.'),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='alternative_farming_advice',
            field=models.JSONField(blank=True, default=list, help_text='General farming tips.'),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='confidence_score',
            field=models.JSONField(blank=True, help_text='Model confidence scores for predictions.', null=True),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='historical_trends',
            field=models.JSONField(blank=True, default=list, help_text='Past weather trends for analysis.'),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='mitigation_suggestions',
            field=models.JSONField(blank=True, default=list, help_text='Suggestions to improve yield.'),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='next_best_action',
            field=models.TextField(blank=True, help_text='Suggested next step for the farmer.', null=True),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='predicted_soil_temp',
            field=models.FloatField(blank=True, help_text='Predicted soil temperature in °C.', null=True),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='predicted_yield',
            field=models.FloatField(blank=True, help_text='AI-predicted raw yield in kg/ha.', null=True),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='weather_summary',
            field=models.TextField(blank=True, help_text='Brief summary of weather conditions.', null=True),
        ),
        migrations.AddField(
            model_name='recommendation',
            name='yield_explanation',
            field=models.JSONField(blank=True, default=list, help_text='Explanation of yield adjustments.'),
        ),
    ]
