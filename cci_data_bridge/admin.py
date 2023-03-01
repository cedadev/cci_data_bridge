from django.contrib import admin

from cci_data_bridge.models import (
    Dataset,
    ECV,
    Filter,
    Project,
    Relationship,
    RelationType,
)


class RelationshipInline(admin.TabularInline):
    model = Relationship
    fk_name = "from_dataset"
    extra = 0


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "dataset_provider",
    )
    inlines = [RelationshipInline]


@admin.register(ECV)
class ECVAdmin(admin.ModelAdmin):
    pass


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display = ("from_dataset", "to_dataset")


@admin.register(RelationType)
class RelationTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
    )


@admin.register(Filter)
class FilterAdmin(admin.ModelAdmin):
    pass
