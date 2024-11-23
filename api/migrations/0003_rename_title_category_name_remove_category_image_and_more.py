# Generated by Django 4.2 on 2024-11-22 01:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_user_options_alter_bookmark_table_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='category',
            old_name='title',
            new_name='name',
        ),
        migrations.RemoveField(
            model_name='category',
            name='image',
        ),
        migrations.AlterField(
            model_name='profile',
            name='image',
            field=models.FileField(blank=True, default='default/default-webp.jpg', null=True, upload_to='image'),
        ),
    ]
