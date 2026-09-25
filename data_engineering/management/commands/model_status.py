from django.core.management.base import BaseCommand

from data_engineering.services.model_registry import (
    load_metadata,
)


class Command(BaseCommand):

    help = "Display the currently registered ML model."

    def handle(self, *args, **options):

        try:
            metadata = load_metadata()

        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING(
                    "No trained model found."
                )
            )
            return

        self.stdout.write(
            f"Model       : {metadata['model_name']}"
        )

        self.stdout.write(
            f"Type        : {metadata['model_type']}"
        )

        self.stdout.write(
            f"Trained at  : {metadata['trained_at']}"
        )

        self.stdout.write(
            f"Train rows  : {metadata['training_rows']}"
        )

        self.stdout.write(
            f"MAE         : {metadata['metrics']['mae']}"
        )

        self.stdout.write(
            f"RMSE        : {metadata['metrics']['rmse']}"
        )

        self.stdout.write(
            f"R2          : {metadata['metrics']['r2']}"
        )

        self.stdout.write(
            f"Features    : {len(metadata['features'])}"
        )