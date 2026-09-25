from django.core.management.base import BaseCommand

from data_engineering.services.ml_model import (
    train_baseline_model,
)


class Command(BaseCommand):

    help = "Train and evaluate the next-stock ML model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            default="DummyJSON",
        )

        parser.add_argument(
            "--min-history",
            type=int,
            default=3,
        )

    def handle(self, *args, **options):

        source = options["source"]
        min_history = options["min_history"]

        self.stdout.write(
            "Preparing temporal ML dataset..."
        )

        result = train_baseline_model(
            source=source,
            min_history=min_history,
        )

        if result["status"] != "success":
            self.stdout.write(
                self.style.ERROR(
                    result.get(
                        "message",
                        "Training failed.",
                    )
                )
            )
            return

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Model training completed."
            )
        )

        self.stdout.write(
            f"Training rows : {result['training_rows']}"
        )

        self.stdout.write(
            f"Test rows     : {result['test_rows']}"
        )

        self.stdout.write(
            f"Features      : {len(result['features'])}"
        )

        self.stdout.write(
            "Removed constant features:"
        )

        for feature in result[
            "removed_constant_features"
        ]:
            self.stdout.write(
                f"  - {feature}"
            )

        metrics = result["metrics"]

        self.stdout.write("")
        self.stdout.write("Evaluation:")
        self.stdout.write(
            f"MAE  : {metrics['mae']:.4f}"
        )
        self.stdout.write(
            f"RMSE : {metrics['rmse']:.4f}"
        )
        self.stdout.write(
            f"R2   : {metrics['r2']:.4f}"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Model saved successfully."
            )
        )