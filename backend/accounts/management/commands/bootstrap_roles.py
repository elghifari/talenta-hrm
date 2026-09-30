from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create business role groups without granting access to any account."

    def handle(self, *args, **options):
        for name in ["HR", "KEPALA_UNIT", "FINANCE", "TECHNICAL_ADMIN", "INTERN"]:
            Group.objects.get_or_create(name=name)
        self.stdout.write("Role groups ready; no accounts or unit grants changed.")
