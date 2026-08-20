from django import forms
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from data_bridge_app.models import (
    ECV,
    Dataset,
    Filter,
    Project,
    Relationship,
    RelationType,
)


class RelationshipInlineForm(forms.ModelForm):

    class Meta:
        model = Relationship
        fields = (
            "target_content_type",
            "target_object_pk",
            "relationships",
            "description",
        )


class OutgoingRelationshipInline(GenericTabularInline):
    model = Relationship
    form = RelationshipInlineForm
    ct_field = "source_content_type"
    ct_fk_field = "source_object_pk"
    extra = 0


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "dataset_provider",
    )
    inlines = [OutgoingRelationshipInline]


@admin.register(ECV)
class ECVAdmin(admin.ModelAdmin):
    pass


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "source_type",
        "target",
        "target_type",
    )


@admin.register(RelationType)
class RelationTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "description",
    )


@admin.register(Filter)
class FilterAdmin(admin.ModelAdmin):
    pass
