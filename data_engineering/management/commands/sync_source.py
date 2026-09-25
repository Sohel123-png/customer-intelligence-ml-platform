from django.core.management.base import BaseCommand

from data_engineering.services.ingestion import APIIngestionService


class Command(BaseCommand):
    help = "Ingest product data from external API"

    def handle(self, *args, **options):

        service = APIIngestionService(
            source_name="DummyJSON",
            url="https://dummyjson.com/products",
            params={
                "limit": 30,
                },
            data_key="products",
        )

        result = service.run()

        self.stdout.write(
            self.style.SUCCESS(
                f"Source: {result['source']}\n"
                f"Created: {result['records_created']}\n"
                f"Updated: {result['records_updated']}"
            )
        )