from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLPattern, URLResolver


def get_view(callback):
    if hasattr(callback, "view_class"):
        view = callback.view_class
    else:
        view = callback
    return view


def get_methods(view):
    methods = []

    for method in ["get", "post", "put", "patch", "delete"]:
        if hasattr(view, method):
            methods.append(method.upper())

    return methods


def walk_patterns(patterns, prefix=""):
    results = []

    for pattern in patterns:

        if isinstance(pattern, URLPattern):
            view = get_view(pattern.callback)
            results.append(
                {
                    "path": prefix + str(pattern.pattern),
                    "name": pattern.name or "",
                    "view": f"{view.__module__}.{view.__name__}",
                    "methods": ",".join(get_methods(view)),
                }
            )

        elif isinstance(pattern, URLResolver):
            nested_prefix = prefix + str(pattern.pattern)
            results.extend(walk_patterns(pattern.url_patterns, nested_prefix))

    return results


class Command(BaseCommand):
    help = "List all URLs in the project"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sort",
            choices=["path", "name", "view"],
            default="path",
            help="Field used for sorting (default: path)",
        )

    def handle(self, *args, **options):
        resolver = get_resolver()
        urls = walk_patterns(resolver.url_patterns)

        sort_key = options["sort"]
        urls = sorted(urls, key=lambda u: u[sort_key])

        for u in urls:
            path = u["path"]
            name = u["name"] or "-"
            view = u["view"]
            methods = u["methods"]

            self.stdout.write(f"{path:100} {name:50} {view:100} {methods:20}")
