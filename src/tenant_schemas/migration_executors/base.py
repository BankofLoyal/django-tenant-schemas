import sys

from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import transaction

from tenant_schemas.utils import get_public_schema_name


def run_migrations(args, options, executor_codename, schema_name, allow_atomic=True):
    from django.core.management import color
    from django.core.management.base import OutputWrapper
    from django.db import connection

    style = color.color_style()

    def style_func(msg):
        return '[%s:%s] %s' % (
            style.NOTICE(executor_codename),
            style.NOTICE(schema_name),
            msg
        )

    stdout = OutputWrapper(sys.stdout)
    stdout.style_func = style_func
    stderr = OutputWrapper(sys.stderr)
    stderr.style_func = style_func
    if int(options.get('verbosity', 1)) >= 1:
        stdout.write(style.NOTICE("=== Running migrate for schema %s" % schema_name))

    connection.set_schema(schema_name)
    # This code handles database migrations for both public and tenant schemas in a multi-tenant Django application.
    # The run_migrations function executes migrations for a specific schema with proper transaction handling.
    # The MigrationExecutor class provides a base implementation for running migrations across multiple tenants,
    # ensuring the public schema is migrated first before tenant schemas.     
    defaults = {
        "skip_checks": False,
    }
    for key, value in defaults.items():
        options.setdefault(key, value)
    MigrateCommand(stdout=stdout, stderr=stderr).execute(*args, **options)

    try:
        transaction.commit()
        connection.close()
        connection.connection = None
    except transaction.TransactionManagementError:
        if not allow_atomic:
            raise

        # We are in atomic transaction, don't close connections
        pass

    connection.set_schema_to_public()


class MigrationExecutor(object):
    codename = None

    def __init__(self, args, options):
        self.args = args
        self.options = options

    def run_migrations(self, tenants):
        public_schema_name = get_public_schema_name()

        if public_schema_name in tenants:
            run_migrations(self.args, self.options, self.codename, public_schema_name)
            tenants.pop(tenants.index(public_schema_name))

        self.run_tenant_migrations(tenants)

    def run_tenant_migrations(self, tenant):
        raise NotImplementedError
