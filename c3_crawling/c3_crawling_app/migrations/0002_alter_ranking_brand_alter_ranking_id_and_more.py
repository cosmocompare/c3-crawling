# Generated by Django 5.1.4 on 2024-12-22 08:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('c3_crawling_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ranking',
            name='brand',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='ranking',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='ranking',
            name='oy_price',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ranking',
            name='price',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ranking',
            name='zz_price',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterModelTable(
            name='ranking',
            table=None,
        ),
    ]