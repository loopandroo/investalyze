# Generated by Django 3.1.7 on 2021-03-24 23:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investalyze', '0002_auto_20210324_2316'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='time',
            field=models.DateTimeField(),
        ),
        migrations.AlterUniqueTogether(
            name='order',
            unique_together={('ticker', 'side', 'quantity', 'price', 'time', 'user')},
        ),
    ]
