import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
from django.apps import apps
from django.db import connection
from django.db.models import AutoField, BigAutoField

django.setup()

reset_count = 0
with connection.cursor() as cursor:
    for model in apps.get_models():
        pk = model._meta.pk
        if not isinstance(pk, (AutoField, BigAutoField)):
            continue

        table = model._meta.db_table
        column = pk.column
        cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", [table, column])
        sequence_name = cursor.fetchone()[0]
        if not sequence_name:
            continue

        quoted_table = connection.ops.quote_name(table)
        quoted_column = connection.ops.quote_name(column)
        cursor.execute(
            f"""
            SELECT setval(
                %s,
                COALESCE((SELECT MAX({quoted_column}) FROM {quoted_table}), 1),
                (SELECT COUNT(*) FROM {quoted_table}) > 0
            )
            """,
            [sequence_name],
        )
        reset_count += 1

print(f"reset_sequences {reset_count}")
