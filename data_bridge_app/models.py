from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models


class RelationType(models.Model):
    name = models.CharField(
        max_length=50,
        primary_key=True,
    )

    description = models.TextField(
        blank=True,
    )

    def __str__(self):
        return self.name


class Relationship(models.Model):
    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    source_object_pk = models.CharField()
    source = GenericForeignKey(
        "source_content_type",
        "source_object_pk",
    )

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    target_object_pk = models.CharField()
    target = GenericForeignKey(
        "target_content_type",
        "target_object_pk",
    )

    relationships = models.ManyToManyField(RelationType)
    description = models.TextField(blank=True)

    def source_type(self):
        return self.source_content_type.model

    def target_type(self):
        return self.target_content_type.model

    def __str__(self):
        names = []
        for relationship in self.relationships.all():
            names.append(relationship.name)
        return ", ".join(names)

    def relationship_type_names(self):
        names = []
        for relationship in self.relationships.all():
            names.append(relationship.name)
        html = "</p><p>".join(names)
        if html != "":
            html = f"<p>{html}</p>"
        return html


class ECV(models.Model):
    name = models.CharField(
        "ECV",
        max_length=50,
        primary_key=True,
    )

    class Meta:
        verbose_name_plural = "ECVs"

    def __str__(self):
        return self.name


class Filter(models.Model):
    name = models.CharField(
        "Parameter name",
        max_length=50,
        help_text="Name of the parameter.",
    )

    value = models.CharField(
        "Parameter value",
        max_length=150,
        help_text="Value of the parameter.",
        blank=False,
        null=False,
    )

    def __str__(self):
        return f"{self.name}={self.value}"


class AiCategory(models.Model):
    name = models.CharField(
        "Parameter name",
        max_length=50,
        help_text="Name of the parameter.",
        primary_key=True,
    )


class AiType(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "category"],
                name="unique_ai_type",
            )
        ]

    name = models.CharField(
        "Parameter name",
        max_length=50,
        help_text="Name of the parameter.",
    )

    category = models.ForeignKey(
        AiCategory,
        on_delete=models.CASCADE,
        blank=False,
    )


class AiUse(models.Model):
    name = models.CharField(
        "Parameter name",
        max_length=50,
        help_text="Name of the parameter.",
        primary_key=True,
    )


class Ai(models.Model):

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["type", "use"],
                name="unique_ai",
            )
        ]

    type = models.ForeignKey(AiType, on_delete=models.CASCADE)
    use = models.ForeignKey(AiUse, on_delete=models.CASCADE)

    outgoing_relationships = GenericRelation(
        Relationship,
        content_type_field="source_content_type",
        object_id_field="source_object_pk",
    )

    incoming_relationships = GenericRelation(
        Relationship,
        content_type_field="target_content_type",
        object_id_field="target_object_pk",
    )


class DatasetProvider(models.Model):
    name = models.CharField(
        max_length=50,
        primary_key=True,
    )

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(
        max_length=50,
    )

    dataset_provider = models.ForeignKey(
        DatasetProvider,
        on_delete=models.CASCADE,
        blank=False,
    )

    outgoing_relationships = GenericRelation(
        Relationship,
        content_type_field="source_content_type",
        object_id_field="source_object_pk",
    )

    incoming_relationships = GenericRelation(
        Relationship,
        content_type_field="target_content_type",
        object_id_field="target_object_pk",
    )

    @property
    def related_ais(self):
        ai_ct = ContentType.objects.get_for_model(Ai)

        return Ai.objects.filter(
            pk__in=self.outgoing_relationships.filter(
                target_content_type=ai_ct
            ).values_list(
                "target_object_pk",
                flat=True,
            )
        )

    def __str__(self):
        return self.name


class Dataset(models.Model):
    url = models.URLField(
        "URL",
        help_text="URL of the dataset",
        blank=False,
        null=False,
    )

    dataset_provider = models.ForeignKey(
        DatasetProvider,
        on_delete=models.CASCADE,
        blank=False,
    )

    start_date = models.DateField(
        help_text="Start date of the data within the dataset.",
        blank=True,
        null=True,
    )

    end_date = models.DateField(
        help_text="Start date of the data within the dataset.",
        blank=True,
        null=True,
    )

    ecvs = models.ManyToManyField(
        ECV,
        help_text="List of ECVs the associated with the dataset.",
        blank=False,
    )

    filters = models.ManyToManyField(
        Filter,
        related_name="filter",
        help_text="List of filters to apply to the dataset.",
        blank=True,
    )

    outgoing_relationships = GenericRelation(
        Relationship,
        content_type_field="source_content_type",
        object_id_field="source_object_pk",
    )

    incoming_relationships = GenericRelation(
        Relationship,
        content_type_field="target_content_type",
        object_id_field="target_object_pk",
    )

    @property
    def related_relationships(self):
        return Relationship.objects.filter(source_object_pk=self.id)

    @property
    def related_datasets(self):
        dataset_ct = ContentType.objects.get_for_model(Dataset)

        return Dataset.objects.filter(
            pk__in=self.outgoing_relationships.filter(
                target_content_type=dataset_ct
            ).values_list(
                "target_object_pk",
                flat=True,
            )
        )

    @property
    def related_ais(self):
        ai_ct = ContentType.objects.get_for_model(Ai)

        return Ai.objects.filter(
            pk__in=self.outgoing_relationships.filter(
                target_content_type=ai_ct
            ).values_list(
                "target_object_pk",
                flat=True,
            )
        )

    def __str__(self):
        return self.url
