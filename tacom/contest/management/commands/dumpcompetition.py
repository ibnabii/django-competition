import os
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Dump specified models (Contest, Style, Category) or all if none are specified."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "models",
            nargs="*",
            type=str,
            help="Names of models to dump (Contest, Style, Category)",
        )

    def handle(self, *args, **options):
        # Available models and corresponding model strings
        model_mapping = {
            "contest": "contest.Contest",
            "style": "contest.Style",
            "category": "contest.Category",
        }

        # Determine the models to dump
        model_names = options["models"]
        if model_names:
            invalid_models = [
                name for name in model_names if name.lower() not in model_mapping
            ]
            if invalid_models:
                raise CommandError(
                    f"Invalid model names: {', '.join(invalid_models)}. Available models: Contest, Style, Category"
                )
            models_to_dump = [model_mapping[name.lower()] for name in model_names]
        else:
            # Default to all models if none specified
            models_to_dump = list(model_mapping.values())

        # Define the output folder
        output_dir = os.path.join(settings.BASE_DIR, "contest_data_migration")
        os.makedirs(output_dir, exist_ok=True)

        # Dump each model to a separate JSON file in the output directory
        for model in models_to_dump:
            model_name = model.split(".")[-1].lower()
            output_file = os.path.join(output_dir, f"{model_name}.json")

            # Run `dumpdata` for each model with specified options
            with open(output_file, "w") as f:
                call_command(
                    "dumpdata",
                    model,
                    natural_primary=True,
                    natural_foreign=True,
                    indent=2,
                    stdout=f,
                )
