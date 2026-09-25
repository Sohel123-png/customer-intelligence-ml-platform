import requests

from django.utils import timezone

from data_engineering.services.models import DataSource, RawDataRecord


class APIIngestionService:

    def __init__(
        self,
        source_name,
        url,
        headers=None,
        params=None,
        data_key=None,
    ):
        self.source_name = source_name
        self.url = url
        self.headers = headers or {}
        self.params = params or {}
        self.data_key = data_key

    def fetch_data(self):

        response = requests.get(
            self.url,
            headers=self.headers,
            params=self.params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def save_raw_data(self, data):

        source, _ = DataSource.objects.get_or_create(
            name=self.source_name,
            defaults={
                "source_type": "api",
                "base_url": self.url,
            },
        )

        if self.data_key:

            records = data.get(self.data_key, [])

        elif isinstance(data, list):

            records = data

        else:

            records = [data]

        created_count = 0
        updated_count = 0

        for record in records:

            if not isinstance(record, dict):
                continue

            external_id = str(
                record.get("id")
                or record.get("product_id")
                or record.get("sku")
                or ""
            ).strip()

            if not external_id:
                continue

            _, created = RawDataRecord.objects.update_or_create(
                source=source,
                external_id=external_id,
                defaults={
                    "payload": record,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        source.last_synced_at = timezone.now()

        source.save(
            update_fields=["last_synced_at"]
        )

        return {
            "source": self.source_name,
            "records_created": created_count,
            "records_updated": updated_count,
        }

    def run(self):

        data = self.fetch_data()

        return self.save_raw_data(data)