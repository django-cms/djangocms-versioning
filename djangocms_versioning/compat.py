try:
    from django.db.models.functions import StrIndex
except ImportError:
    # Backport from Django 2.0
    from django.db.models import Func, fields

    class StrIndex(Func):
        """
        Return a positive integer corresponding to the 1-indexed position of the
        first occurrence of a substring inside another string, or 0 if the
        substring is not found.
        """
        function = 'INSTR'
        arity = 2
        output_field = fields.IntegerField()

        def as_postgresql(self, compiler, connection, **extra_context):
            return super().as_sql(compiler, connection, function='STRPOS', **extra_context)
