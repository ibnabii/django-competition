import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Load data for specified models (Contest, Style, Category) from JSON files in the correct order."

    def add_arguments(self, parser):
        parser.add_argument(
            "models",
            nargs="*",
            type=str,
            help="Names of models to load (Contest, Style, Category)",
        )

    def handle(self, *args, **options):
        # Define the loading order and mapping to file names
        model_order = ["contest", "style", "category"]
        model_file_mapping = {
            "contest": "contest.json",
            "style": "style.json",
            "category": "category.json",
        }

        # Determine models to load based on input arguments or default to all
        model_names = options["models"]
        if model_names:
            invalid_models = [
                name for name in model_names if name.lower() not in model_file_mapping
            ]
            if invalid_models:
                raise CommandError(
                    f"Invalid model names: {', '.join(invalid_models)}. Available models: Contest, Style, Category"
                )

            # Respect the order by filtering from `model_order`
            models_to_load = [
                name for name in model_order if name in [m.lower() for m in model_names]
            ]
        else:
            # Default to loading all models in the correct order
            models_to_load = model_order

        # Define the data folder path
        data_dir = os.path.join(settings.BASE_DIR, "contest_data_migration")

        # Load each model's data in the specified order
        for model in models_to_load:
            data_file = os.path.join(data_dir, model_file_mapping[model])
            if not os.path.exists(data_file):
                self.stdout.write(
                    self.style.WARNING(
                        f"No data file found for {model.capitalize()}. Skipping..."
                    )
                )
                continue

            # Load data from the JSON file
            try:
                call_command("loaddata", data_file)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully loaded {model.capitalize()} data."
                    )
                )
            except Exception as e:
                raise CommandError(f"Error loading {model.capitalize()} data: {e}")
