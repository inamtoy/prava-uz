from django.db import migrations


def sync_roles(apps, schema_editor):
    """Rol qoidasini mavjud yozuvlarga qo'llash: superuser -> role=admin, is_staff/is_superuser roldan."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=True).exclude(role="admin").update(role="admin")
    User.objects.filter(role="admin").update(is_staff=True, is_superuser=True)
    User.objects.exclude(role="admin").update(is_staff=False, is_superuser=False)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_alter_user_role")]

    operations = [migrations.RunPython(sync_roles, migrations.RunPython.noop)]
