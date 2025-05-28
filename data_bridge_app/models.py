from django.db import models

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


class Project(models.Model):
    name = models.CharField(
        max_length=50,
        primary_key=True,
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
        Project,
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

    related_datasets = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="+",
        through="Relationship",
        through_fields=("from_dataset", "to_dataset"),
        help_text="List of related datasets.",
    )

    def __str__(self):
        return self.url


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
    from_dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    relationships = models.ManyToManyField(
        RelationType,
        blank=False,
    )

    to_dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="linked_dataset",
    )

    description = models.TextField(
        blank=True,
    )

    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(
    #             fields=("from_dataset", "to_dataset", "relationships"),
    #             name="unique_relationship",
    #         ),
    #     ]

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
