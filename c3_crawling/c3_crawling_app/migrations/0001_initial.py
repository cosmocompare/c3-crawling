# Generated by Django 5.1.4 on 2024-12-22 05:05

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ranking',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('brand', models.CharField(max_length=100)),
                ('cosmetic_name', models.CharField(max_length=200)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('oy_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('zz_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cosmetic_url', models.URLField()),
                ('image_url', models.URLField()),
            ],
            options={
                'db_table': 'ranking',
            },
        ),
    ]
