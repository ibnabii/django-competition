from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Sample command to print "Hello {name}"'

    def add_arguments(self, parser):
        parser.add_argument('name', help='Name to greet')

    def handle(self, *args, **kwargs):
        name = kwargs['name']
        self.stdout.write(f'Hello {name}')
