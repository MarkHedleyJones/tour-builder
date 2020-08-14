# Generated by Django 3.0.6 on 2020-08-02 18:14

import datetime
from django.db import migrations, models
import django.db.models.deletion
from django.utils.timezone import utc


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('available_from', models.DateTimeField(default=datetime.datetime(1969, 12, 31, 14, 41, tzinfo=utc))),
                ('available_until', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 14, 40, 59, tzinfo=utc))),
                ('cost', models.PositiveIntegerField(default=0)),
                ('duration', models.DurationField(default=datetime.timedelta)),
                ('title', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='TrainRide',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duration', models.DurationField(default=datetime.timedelta)),
                ('cost', models.PositiveIntegerField(default=0)),
                ('transfers', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Station',
            fields=[
                ('location_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='tourbuilder.Location')),
                ('station_id', models.IntegerField(unique=True)),
            ],
            bases=('tourbuilder.location',),
        ),
        migrations.CreateModel(
            name='Tour',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('available_from', models.DateTimeField(default=datetime.datetime(1969, 12, 31, 14, 41, tzinfo=utc))),
                ('available_until', models.DateTimeField(default=datetime.datetime(1970, 1, 1, 14, 40, 59, tzinfo=utc))),
                ('cost', models.PositiveIntegerField(default=0)),
                ('duration', models.DurationField(default=datetime.timedelta)),
                ('activities', models.ManyToManyField(to='tourbuilder.Activity')),
                ('train_rides', models.ManyToManyField(to='tourbuilder.TrainRide')),
            ],
        ),
        migrations.AddField(
            model_name='activity',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tourbuilder.Category'),
        ),
        migrations.AddField(
            model_name='trainride',
            name='from_station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='from_station', to='tourbuilder.Station'),
        ),
        migrations.AddField(
            model_name='trainride',
            name='to_station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='to_station', to='tourbuilder.Station'),
        ),
        migrations.AddField(
            model_name='activity',
            name='train_station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tourbuilder.Station'),
        ),
    ]
