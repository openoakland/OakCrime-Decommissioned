# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-12-15 05:17
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dailyIncid', '0004_auto_20190123_0503'),
    ]

    operations = [
        migrations.CreateModel(
            name='BoxID',
            fields=[
                ('idx', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('boxidx', models.BigIntegerField(db_index=True)),
                ('boxModDT', models.DateTimeField()),
                ('froot', models.CharField(db_index=True, max_length=100)),
                ('harvestDT', models.DateTimeField(null=True)),
                ('parseDT', models.DateTimeField(null=True)),
                ('kids', models.ManyToManyField(related_name='parent', to='dailyIncid.BoxID')),
            ],
        ),
        migrations.CreateModel(
            name='CrimeCatMatch',
            fields=[
                ('idx', models.AutoField(primary_key=True, serialize=False)),
                ('matchType', models.CharField(choices=[('cd', 'CrimeType+Desc'), ('c', 'CrimeType'), ('d', 'Desc')], max_length=2)),
                ('ctype', models.CharField(db_index=True, max_length=100)),
                ('desc', models.CharField(db_index=True, max_length=100)),
                ('crimeCat', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='DailyParse',
            fields=[
                ('idx', models.AutoField(primary_key=True, serialize=False)),
                ('froot', models.CharField(db_index=True, max_length=100)),
                ('parseDT', models.DateTimeField(null=True)),
                ('parseOrder', models.IntegerField(default=0)),
                ('opd_rd', models.CharField(db_index=True, max_length=10)),
                ('incidDT', models.DateTimeField(null=True)),
                ('parseDict', django.contrib.postgres.fields.jsonb.JSONField(default={})),
                ('boxobj', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dailyIncid.BoxID')),
            ],
        ),
        migrations.CreateModel(
            name='OCUpdate',
            fields=[
                ('idx', models.AutoField(primary_key=True, serialize=False)),
                ('opd_rd', models.CharField(db_index=True, max_length=10)),
                ('oidx', models.IntegerField(default=0)),
                ('newSrc', models.CharField(max_length=50)),
                ('fieldName', models.CharField(max_length=20)),
                ('prevVal', models.CharField(max_length=200)),
                ('newVal', models.CharField(max_length=200)),
                ('prevSocDT', models.DateTimeField(null=True)),
                ('newSocDT', models.DateTimeField(null=True)),
                ('lastModDateTime', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='PC2CC',
            fields=[
                ('idx', models.AutoField(primary_key=True, serialize=False)),
                ('pc', models.CharField(max_length=30)),
                ('crimeCat', models.CharField(max_length=100)),
            ],
        ),
        migrations.RemoveField(
            model_name='crimecat',
            name='ctypeDesc',
        ),
        migrations.AddField(
            model_name='oakcrime',
            name='socrataDT',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='crimecat',
            name='crimeCat',
            field=models.CharField(max_length=50),
        ),
    ]