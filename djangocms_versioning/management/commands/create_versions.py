from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError

from djangocms_versioning import constants
from djangocms_versioning.conf import DEFAULT_USER, USERNAME_FIELD
from djangocms_versioning.models import Version
from djangocms_versioning.versionables import _cms_extension


User = get_user_model()


class Command(BaseCommand):
    help = 'Creates Version objects for versioned models lacking one. If the DJANGOCMS_VERSIONING_DEFAULT_USER ' \
           'setting is not populated you will have to provide either the --userid or --username option for ' \
           'each Version object needs to be assigned to a user.'

    def add_arguments(self, parser):
        parser.add_argument(
            "--state",
            type=str,
            default=constants.DRAFT,
            choices=[key for key, value in constants.VERSION_STATES],
            help=f"state of newly created version object (defaults to {constants.DRAFT})"
        )
        parser.add_argument(
            "--username",
            type=str,
            help="Username of user to create the missing Version objects"
        )
        parser.add_argument(
            "--userid",
            type=int,
            help="User id of user to create the missing Version objects"
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not change the database",
        )

    def get_user(self, options):
        if DEFAULT_USER is not None:
            try:
                return User.objects.get(pk=DEFAULT_USER)
            except User.DoesNotExist:
                raise CommandError(f"No user with id {DEFAULT_USER} found "
                                   f"(specified as DJANGOCMS_VERSIONING_DEFAULT USER in settings.py")

        if options["userid"] and options["username"]:
            raise CommandError("Only either one of the options '--userid' or '--username' may be given")
        if options["userid"]:
            try:
                return User.objects.get(pk=options["userid"])
            except User.DoesNotExist:
                raise CommandError(f"No user with id {options['userid']} found")
        if options["username"]:
            try:
                return User.objects.get(**{USERNAME_FIELD: options["username"]})
            except User.DoesNotExist:
                raise CommandError(f"No user with name {options['username']} found")
        return None

    def handle(self, *args, **options):
        user = self.get_user(options)

        for versionable in _cms_extension().versionables:
            Model = versionable.content_model
            content_type = ContentType.objects.get_for_model(Model)
            version_ids = Version.objects.filter(content_type_id=content_type.pk).values_list("object_id", flat=True)
            unversioned = Model.admin_manager.exclude(pk__in=version_ids).order_by("-pk")
            self.stdout.write(self.style.NOTICE(
                f"{len(version_ids) + len(unversioned)} objects of type {Model.__name__}, thereof "
                f"{len(unversioned)} missing Version object"
            ))
            if not options["dry_run"]:
                if user is None:
                    raise CommandError("Please specify a user which missing Version objects shall belong to "
                                       "either with the DJANGOCMS_VERSIONING_DEFAULT_USER setting or using "
                                       "command line arguments")
                for orphan in unversioned:
                    try:
                        Version.objects.create(
                            content=orphan,
                            state=options["state"],
                            created_by=user,
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f"Successfully created version object for {Model.__name__} with pk={orphan.pk}"
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Failed creating version object for {Model.__name__} with pk={orphan.pk}: {e}"
                        ))
