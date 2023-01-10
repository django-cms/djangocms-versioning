from django.core.management.base import BaseCommand, CommandError

from djangocms_versioning import constants
from djangocms_versioning.models import Version
from djangocms_versioning.versionables import _cms_extension


# from polls.models import Question as Poll

class Command(BaseCommand):
    help = 'Creates Version objects for versioned models lacking one'

    def add_arguments(self, parser):
        parser.add_argument("state", type=str, default=constants.DRAFT)

    def get_user(self, options):
        pass

    def handle(self, *args, **options):
        if options["state"] not in dict(constants.VERSION_STATES):
            raise CommandError(f"state needs to be one of {', '.join(key for key, value in constants.VERSION_STATES)}")
        user = self.get_user(options)
        versionables = _cms_extension().versionables
        print(f"{versionables=}")
        for model in versionables:
            pass

        self.stdout.write(self.style.SUCCESS('Successfully closed poll "%s"' % 1))
