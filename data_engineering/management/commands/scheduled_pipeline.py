import time

from django.core.management.base import BaseCommand

from django.core.management import call_command


class Command(BaseCommand):
    help = "Run the data pipeline continuously at a fixed interval."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=300,
            help="Interval between pipeline runs in seconds.",
        )

    def handle(self, *args, **options):

        interval = options["interval"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduler started. "
                f"Pipeline will run every {interval} seconds."
            )
        )

        while True:

            self.stdout.write(
                "\nRunning pipeline..."
            )

            try:
                call_command(
                    "run_pipeline"
                )

            except Exception as error:

                self.stdout.write(
                    self.style.ERROR(
                        f"Pipeline failed: {error}"
                    )
                )

            self.stdout.write(
                f"\nWaiting {interval} seconds..."
            )

            time.sleep(interval)