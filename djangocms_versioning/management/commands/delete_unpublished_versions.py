from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, ProtectedError
from django.utils import timezone

from djangocms_versioning import conf, constants
from djangocms_versioning.models import Version
from djangocms_versioning.versionables import _cms_extension

#: Values of ``DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS`` that permit deletion.
#: ``True`` is the legacy spelling of :data:`~djangocms_versioning.constants.DELETE_ANY`.
DELETION_ENABLED = (constants.DELETE_ANY, constants.DELETE_NON_PUBLIC_ONLY, True)

DEFAULT_DAYS = 90
DEFAULT_BATCH_SIZE = 1000


class Command(BaseCommand):
    help = (
        "Deletes unpublished versions and their content objects if they have not been touched for a "
        f"given number of days ({DEFAULT_DAYS} by default). Archived versions can be included with "
        "--archived. Draft and published versions are never deleted. Requires the setting "
        "DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS to allow deleting versions."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=DEFAULT_DAYS,
            help=f"Delete versions untouched for at least this many days (defaults to {DEFAULT_DAYS})",
        )
        parser.add_argument(
            "--archived",
            action="store_true",
            help="Also delete archived versions, not just unpublished ones",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be deleted, do not change the database",
        )
        parser.add_argument(
            "--model",
            action="append",
            dest="models",
            metavar="app_label.ModelName",
            help="Only consider this content model (repeat the option for several models)",
        )
        parser.add_argument(
            "--date-field",
            choices=("modified", "created"),
            default="modified",
            help="Version field the age is measured on (defaults to 'modified')",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help=f"Number of content objects deleted per query (defaults to {DEFAULT_BATCH_SIZE})",
        )
        parser.add_argument(
            "--delete-empty-groupers",
            action="store_true",
            help="Also delete grouper objects that are left without any content object",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do not prompt for confirmation before deleting",
        )

    def handle(self, *args, **options):
        if conf.ALLOW_DELETING_VERSIONS not in DELETION_ENABLED:
            raise CommandError(
                "Deleting versions is not enabled. Set DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS to "
                f'"{constants.DELETE_ANY}" or "{constants.DELETE_NON_PUBLIC_ONLY}" in settings.py to '
                "allow this command to delete versions."
            )
        if options["days"] < 0:
            raise CommandError("--days must not be negative")
        if options["batch_size"] < 1:
            raise CommandError("--batch-size must be at least 1")

        self.verbosity = options["verbosity"]
        self.batch_size = options["batch_size"]
        self.delete_empty_groupers = options["delete_empty_groupers"]

        states = [constants.UNPUBLISHED]
        if options["archived"]:
            states.append(constants.ARCHIVED)
        cutoff = timezone.now() - timedelta(days=options["days"])
        described_states = " or ".join(states)

        versionables = self.get_versionables(options["models"])
        queryset = self.get_queryset(states, cutoff, versionables, options["date_field"])

        # Group the work by content type so that content objects can be deleted in bulk
        counts = dict(
            queryset.values_list("content_type_id")
            .order_by()
            .annotate(count=Count("pk"))
            .values_list("content_type_id", "count")
        )
        total = sum(counts.values())

        if not total:
            self.stdout.write(self.style.NOTICE(
                f"No {described_states} version older than {options['days']} day(s) found."
            ))
            return

        self.stdout.write(self.style.NOTICE(
            f"{total} {described_states} version(s) last {options['date_field']} before "
            f"{cutoff.isoformat(timespec='seconds')}:"
        ))
        for content_type_id, count in counts.items():
            self.stdout.write(f"  {self.label_for(content_type_id)}: {count}")

        if options["dry_run"]:
            self.stdout.write(self.style.NOTICE("Dry run: no changes have been made."))
            return
        if options["interactive"] and not self.confirm():
            self.stdout.write(self.style.NOTICE("Aborted: no changes have been made."))
            return

        deleted = 0
        protected = 0
        for content_type_id in counts:
            content_type_deleted, content_type_protected = self.delete_for_content_type(
                queryset, content_type_id, versionables[content_type_id]
            )
            deleted += content_type_deleted
            protected += content_type_protected

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} version(s)."))
        if protected:
            self.stdout.write(self.style.WARNING(
                f"{protected} version(s) were kept: their content object is protected by a foreign key."
            ))

    def get_versionables(self, model_labels: list | None) -> dict:
        """Map content type id -> versionable, optionally limited to the content models
        given as ``app_label.ModelName`` labels."""
        versionables_by_label = {
            versionable.content_model._meta.label_lower: versionable
            for versionable in _cms_extension().versionables
            if versionable.concrete
        }
        if model_labels:
            selected = []
            for label in model_labels:
                versionable = versionables_by_label.get(label.lower())
                if versionable is None:
                    raise CommandError(
                        f"{label} is not a versioned content model. Available models: "
                        f"{', '.join(sorted(versionables_by_label))}"
                    )
                selected.append(versionable)
        else:
            selected = versionables_by_label.values()

        return {
            content_type_id: versionable
            for versionable in selected
            for content_type_id in versionable.content_types
        }

    def get_queryset(self, states: list, cutoff, versionables: dict, date_field: str):
        queryset = Version.objects.filter(
            state__in=states,
            content_type_id__in=versionables.keys(),
            **{f"{date_field}__lt": cutoff},
        )
        if conf.ALLOW_DELETING_VERSIONS == constants.DELETE_NON_PUBLIC_ONLY:
            # Versions that are the source of a published version are protected from deletion.
            # Leave them out instead of running into a ProtectedError for each of them.
            sources_of_published = Version.objects.filter(
                state=constants.PUBLISHED, source__isnull=False
            ).values_list("source_id", flat=True)
            queryset = queryset.exclude(pk__in=sources_of_published)
        return queryset

    @staticmethod
    def label_for(content_type_id: int) -> str:
        model = ContentType.objects.get_for_id(content_type_id).model_class()
        return model._meta.label if model else f"<unknown content type {content_type_id}>"

    @staticmethod
    def confirm() -> bool:
        answer = input("This will permanently delete the content objects listed above. Continue? [y/N] ")
        return answer.lower() in ("y", "yes")

    def delete_for_content_type(self, queryset, content_type_id: int, versionable) -> tuple[int, int]:
        """Delete the content objects of a single content type in batches. Deleting a content
        object cascades to its ``Version`` through the injected ``versions`` generic relation."""
        model = ContentType.objects.get_for_id(content_type_id).model_class()
        if model is None:
            self.stdout.write(self.style.WARNING(
                f"Skipping content type {content_type_id}: its model is no longer installed."
            ))
            return 0, 0

        deleted = 0
        protected = 0
        grouper_ids = set()
        grouper_field = versionable.grouper_field.attname
        # Walk the versions by primary key so that objects which cannot be deleted
        # do not make the next batch return the same rows again.
        last_pk = 0
        while True:
            batch = list(
                queryset.filter(content_type_id=content_type_id, pk__gt=last_pk)
                .order_by("pk")
                .values_list("pk", "object_id")[:self.batch_size]
            )
            if not batch:
                break
            last_pk = batch[-1][0]
            object_ids = [object_id for _, object_id in batch]
            content_objects = model._base_manager.filter(pk__in=object_ids)
            if self.delete_empty_groupers:
                grouper_ids.update(content_objects.values_list(grouper_field, flat=True))
            batch_deleted, batch_protected = self.delete_batch(model, object_ids)
            deleted += batch_deleted
            protected += batch_protected
            if self.verbosity > 1:
                self.stdout.write(f"  {model._meta.label}: {deleted} version(s) deleted")

        if self.delete_empty_groupers and grouper_ids:
            self.delete_groupers_without_content(versionable, grouper_ids)
        return deleted, protected

    def delete_batch(self, model, object_ids: list) -> tuple[int, int]:
        """Delete one batch of content objects, falling back to single deletions if the
        batch as a whole is protected by a foreign key."""
        try:
            with transaction.atomic():
                return self.count_deleted_versions(model._base_manager.filter(pk__in=object_ids).delete()), 0
        except ProtectedError:
            pass

        deleted = 0
        protected = 0
        for object_id in object_ids:
            try:
                with transaction.atomic():
                    deleted += self.count_deleted_versions(model._base_manager.filter(pk=object_id).delete())
            except ProtectedError as error:
                protected += 1
                if self.verbosity > 0:
                    self.stdout.write(self.style.WARNING(
                        f"  Cannot delete {model._meta.label} pk={object_id}: {error}"
                    ))
        return deleted, protected

    @staticmethod
    def count_deleted_versions(delete_result: tuple) -> int:
        return delete_result[1].get(Version._meta.label, 0)

    def delete_groupers_without_content(self, versionable, grouper_ids: set):
        """Delete groupers that have lost their last content object, mirroring what
        ``Version.delete()`` does when the last version of a grouper is deleted."""
        grouper_field = versionable.grouper_field.attname
        still_used = set(
            versionable.content_model._base_manager.filter(
                **{f"{grouper_field}__in": grouper_ids}
            ).values_list(grouper_field, flat=True)
        )
        empty = {grouper_id for grouper_id in grouper_ids if grouper_id is not None} - still_used
        if not empty:
            return
        try:
            with transaction.atomic():
                versionable.grouper_model._base_manager.filter(pk__in=empty).delete()
        except ProtectedError as error:
            self.stdout.write(self.style.WARNING(
                f"  Cannot delete empty {versionable.grouper_model._meta.label} objects: {error}"
            ))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {len(empty)} empty {versionable.grouper_model._meta.label} object(s)."
        ))
