from django.core.management.base import BaseCommand

from employees.import_service import prune_batches


class Command(BaseCommand):
    help = "Remove expired employee-import drafts and receipts older than one day."

    def handle(self, *args, **options):
        self.stdout.write(f"Removed {prune_batches()} expired import records.")
