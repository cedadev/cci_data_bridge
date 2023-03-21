"""
Views

The "home" view redirects to "/dataset/" (DatasetListView) which lists all data sets

The "DatasetListView" displays all datasets and allows filtering on url, filters,
provider, ecv

The "DatasetDetailView" displays a dataset based on an internal id

The "DatasetUrlDetailView" gets data based on a dataset URL. If there is only one
dataset for the url then display a detail view, otherwise display a list of datasets

"""

from django.db.models import Q
from django.http import Http404, JsonResponse
from django.http.response import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from plotly.offline import plot
import plotly.graph_objects as go

from cci_data_bridge.models import Dataset, ECV, Project, Relationship, RelationType


SANKEY_COLOUR_1 = "rgba(230, 159, 0, 1.0)"
SANKEY_COLOUR_2 = "rgba(86, 180, 233, 1.0)"
SANKEY_COLOUR_3 = "rgba(0, 158, 115, 1.0)"
SANKEY_COLOUR_4 = "rgba(240, 228, 66, 1.0)"
SANKEY_COLOUR_5 = "rgba(0, 114, 178 , 1.0)"
SANKEY_COLOUR_6 = "rgba(213, 94, 0, 1.0)"
SANKEY_COLOUR_7 = "rgba(204, 121, 167, 1.0)"
SANKEY_COLOUR_8 = "rgba(0, 0, 0, 1.0)"
SANKEY_FADE = "0.4"

# pylint: disable=C0330


class ImageResponseMixin:
    """
    A mixin that can be used to render an image.

    """

    def render_to_image_response(self, context, filename, format_):
        """
        Returns a byte response, transforming "context" to make the payload.

        """
        filename = f"{filename}.{format_}"
        if format_ == "svg":
            filename = f"{filename}.+xml"

        dataset = context.get("figure").to_image(format=format_)
        response = HttpResponse(
            dataset,
            content_type=f"image/{format_}",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class JSONResponseMixin:
    """
    A mixin that can be used to render a JSON response.

    """

    def render_to_json_response(self, context):
        """
        Returns a JSON response, transforming "context" to make the payload.

        """
        if context.get("object") is not None:
            return JsonResponse(
                self.get_j_data(context["object"], context["relationships"]),
                safe=False,
            )

        data = []
        for obj in context["object_list"]:
            data.append(
                self.get_j_data(obj, Relationship.objects.filter(from_dataset=obj))
            )

        return JsonResponse(
            data,
            safe=False,
        )

    def get_j_data(self, dataset, relationships):
        """
        Returns an object that will be serialized as JSON by json.dumps().

        """

        data = {}
        data["url"] = dataset.url
        data["dataset_provider"] = dataset.dataset_provider_id

        ecvs = []
        for ecv in dataset.ecvs.values("name"):
            ecvs.append(ecv["name"])
        if len(ecvs) > 0:
            data["ecvs"] = ecvs

        filters = []
        for filter_ in dataset.filters.all():
            filters.append({filter_.name: filter_.value})
        if len(filters) > 0:
            data["filters"] = filters

        combiened_relationships = {}
        for rel in relationships:
            if rel.to_dataset.id in combiened_relationships.keys():
                combiened_relationships[rel.to_dataset.id]["relationship_types"].append(
                    str(rel)
                )
            else:
                relationship = {
                    "relationship_types": [str(rel)],
                    "related_dataset": str(rel.to_dataset),
                    "related_dataset_start_date": rel.to_dataset.start_date,
                    "related_dataset_end_date": rel.to_dataset.end_date,
                    "description": rel.description,
                }
                combiened_relationships[rel.to_dataset.id] = relationship

            filters = []
            for filter_ in rel.to_dataset.filters.all():
                filters.append({filter_.name: filter_.value})
            if len(filters) > 0:
                relationship["filters"] = filters

            relationship["related_dataset_start_date"] = rel.to_dataset.start_date
            relationship["related_dataset_end_date"] = rel.to_dataset.end_date

        data["relationships"] = list(combiened_relationships.values())
        return data


class HomeView(RedirectView):
    url = "/dataset/"


class DatasetListView(JSONResponseMixin, ListView):
    model = Dataset

    def render_to_response(self, context):
        # Look for a 'format=json' GET argument
        if (
            self.request.GET.get("format") == "json"
            or self.request.content_type == "application/json"
        ):
            return self.render_to_json_response(context)

        if len(context["dataset_list"]) == 1:
            id_ = context["dataset_list"][0].id
            return redirect("dataset-detail", pk=id_)

        return super().render_to_response(context)

    def get_queryset(self):
        url = self.request.GET.get("url")
        filters = self.request.GET.get("filters")
        provider = self.request.GET.get("provider")
        ecv = self.request.GET.get("ecv")

        return get_queryset(url, filters, provider, ecv)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ecvs"] = ECV.objects.all().order_by("name")
        return context


class DatasetDetailView(JSONResponseMixin, DetailView):
    model = Dataset

    def render_to_response(self, context):
        # Look for a 'format=json' GET argument
        if (
            self.request.GET.get("format") == "json"
            or self.request.content_type == "application/json"
        ):
            return self.render_to_json_response(context)

        # return html
        return super().render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ds_id = self.kwargs["pk"]
        dataset = Dataset.objects.get(id=ds_id)
        context["relationships"] = Relationship.objects.filter(from_dataset=dataset)

        title = f"Sankey Diagram for the {dataset.url} Dataset"
        snakey_diagram = SankeyDiagram([dataset], title)
        context["plot_div"] = snakey_diagram.plot_div()

        return context


class DatasetUrlDetailView(JSONResponseMixin, ListView):
    """
    When using a URL to select the datasets you may get multiple results.

    If there is only one result display the detail page.
    If there are more than one result then display the list page.

    """

    model = Dataset
    template_name = "cci_data_bridge/dataset_list.html"

    def render_to_response(self, context):
        if len(context["dataset_list"]) == 0:
            raise Http404("Dataset not found")

        # Look for a 'format=json' GET argument
        if (
            self.request.GET.get("format") == "json"
            or self.request.content_type == "application/json"
        ):
            return self.render_to_json_response(context)

        if len(context["dataset_list"]) == 1:
            # return html detail page
            dataset = context["object_list"][0]
            context["object"] = dataset
            context["relationships"] = Relationship.objects.filter(from_dataset=dataset)
            title = f"Sankey Diagram for the {dataset.url} Dataset"
            snakey_diagram = SankeyDiagram([dataset], title)
            context["plot_div"] = snakey_diagram.plot_div()

            return TemplateResponse(
                self.request, "cci_data_bridge/dataset_detail.html", context
            )

        return super().render_to_response(context)

    def get_queryset(self):
        url = _fix_url(self.kwargs["url"])
        return Dataset.objects.filter(url=url)


def get_queryset(url=None, filters=None, provider=None, ecv=None):
    if url is not None and url != "":
        # get the datasets for the given url
        datasets = Dataset.objects.all().filter(url=url)
    else:
        # get all datasets
        datasets = Dataset.objects.all().order_by("url")

    if provider is not None and provider != "":
        # get the datasets for the given provider
        datasets = datasets.filter(dataset_provider=provider)

    if ecv is not None and ecv != "":
        # get the datasets for the given ecv
        datasets = datasets.filter(ecvs=ecv)

    if filters is None or filters == "" or filters == "*":
        # your job here is done
        return datasets

    # now filter with the filters
    filters = filters.split(",")
    filter_count = len(filters)

    # first pass remove any results that do not have the same number of filters
    datasets_to_exclude = []
    for dataset in datasets:
        if len(dataset.filters.all()) != filter_count:
            datasets_to_exclude.append(dataset.id)

    for exclude in datasets_to_exclude:
        datasets = datasets.exclude(id=exclude)

    # now need to make sure filters match
    filter_dict = {}
    for filter_ in filters:
        name, value = filter_.split("=")
        filter_dict[name] = value

    datasets_to_exclude = []
    for dataset in datasets:
        for dataset_filter in dataset.filters.all():
            if filter_dict.get(dataset_filter.name) != dataset_filter.value:
                datasets_to_exclude.append(dataset.id)
                # no need to check the rest of the filters
                break

    for exclude in datasets_to_exclude:
        datasets = datasets.exclude(id=exclude)

    return datasets


class DocsApiView(TemplateView):
    template_name = "cci_data_bridge/api_doc.html"


class ProjectListView(ListView):
    model = Project

    def render_to_response(self, context):
        # Look for a 'format=json' GET argument
        if (
            self.request.GET.get("format") == "json"
            or self.request.content_type == "application/json"
        ):
            data = []
            for obj in context["object_list"].all():
                data.append(obj.name)
            return JsonResponse(
                data,
                safe=False,
            )

        return super().render_to_response(context)


class RelationTypeListView(ListView):
    model = RelationType

    def render_to_response(self, context):
        # Look for a 'format=json' GET argument
        if (
            self.request.GET.get("format") == "json"
            or self.request.content_type == "application/json"
        ):
            return JsonResponse((list(context["object_list"].values())), safe=False)

        return super().render_to_response(context)


class SankeyView(RedirectView):
    url = "/sankey/cci"


class SankeyProjectView(ImageResponseMixin, TemplateView):
    template_name = "cci_data_bridge/sankey.html"

    def render_to_response(self, context):
        # Look for a 'format=png' GET argument
        if (
            self.request.GET.get("format") == "png"
            or self.request.content_type == "image/png"
        ):
            filename = f"{context.get('project')}-sankey"
            return self.render_to_image_response(context, filename, "png")
        # Look for a 'format=svg' GET argument
        if (
            self.request.GET.get("format") == "svg"
            or self.request.content_type == "image/svg+xml"
        ):
            filename = f"{context.get('project')}-sankey"
            return self.render_to_image_response(context, filename, "svg")
        # Look for a 'format=jpeg' GET argument
        if (
            self.request.GET.get("format") == "jpeg"
            or self.request.content_type == "image/jpeg"
        ):
            filename = f"{context.get('project')}-sankey"
            return self.render_to_image_response(context, filename, "jpeg")

        # return html
        context["plot_div"] = plot(context["figure"], output_type="div")
        context["figure"] = None
        return super().render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        context = super(SankeyProjectView, self).get_context_data(*args, **kwargs)

        project = self.kwargs["project"]
        if project.lower() == "cci":
            datasets = Dataset.objects.filter(
                Q(dataset_provider="CCI Open Data Portal")
                | Q(dataset_provider="CCI Archive on CEDA")
            )
            project = "CCI"
        elif project.lower() == "c3s":
            datasets = Dataset.objects.filter(dataset_provider="C3S Climate Data Store")
            project = "C3S"
        else:
            # could be an ecv
            datasets = Dataset.objects.filter(ecvs=project)

        if len(datasets.all()) == 0:
            raise Http404(f"Project not found")

        title = f"Sankey Diagram for {project} Datasets"
        snakey_diagram = SankeyDiagram(datasets, title)
        context["figure"] = snakey_diagram.get_figure()
        context["project"] = project

        context["dataset_list"] = (
            Dataset.objects.values("url").order_by("url").distinct()
        )

        return context


class SankeyDatasetView(ImageResponseMixin, TemplateView):
    template_name = "cci_data_bridge/sankey.html"

    def render_to_response(self, context):
        # Look for a 'format=png' GET argument
        if (
            self.request.GET.get("format") == "png"
            or self.request.content_type == "image/png"
        ):
            filename = f"{context.get('dataset_url')}-sankey"
            return self.render_to_image_response(context, filename, "png")
        # Look for a 'format=svg' GET argument
        if (
            self.request.GET.get("format") == "svg"
            or self.request.content_type == "image/svg"
        ):
            filename = f"{context.get('dataset_url')}-sankey"
            return self.render_to_image_response(context, filename, "svg")
        # Look for a 'format=jpeg' GET argument
        if (
            self.request.GET.get("format") == "jpeg"
            or self.request.content_type == "image/jpeg"
        ):
            filename = f"{context.get('dataset_url')}-sankey"
            return self.render_to_image_response(context, filename, "jpeg")

        # return html
        context["plot_div"] = plot(context["figure"], output_type="div")
        context["figure"] = None
        return super().render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        context = super(SankeyDatasetView, self).get_context_data(*args, **kwargs)

        dataset_url = _fix_url(self.kwargs["url"])
        datasets = Dataset.objects.filter(url=dataset_url)
        if len(datasets.all()) == 0:
            raise Http404(f"Dataset not found")

        title = f"Sankey Diagram for the {dataset_url} Dataset"
        snakey_diagram = SankeyDiagram(datasets, title)
        context["figure"] = snakey_diagram.get_figure()
        context["dataset_url"] = dataset_url

        context["dataset_list"] = (
            Dataset.objects.values("url").order_by("url").distinct()
        )

        return context


class SankeyDiagram:
    """
    Produce a Sankey diagram.

    """

    def __init__(self, datasets, title):
        self.datasets = datasets
        self.title = title
        self.dataset_url = None
        self.filters = {}
        self.last_id = -1
        # nodes can be datasets or filters
        self.nodes = {}
        self.node_names = {}
        self.duplicates = {}
        self.links = {}
        self.node_colours = {}
        self.link_colours = []
        self.link_names = []

    def get_figure(self):
        """
        Generate a figure containing the Sankey diagram.

        """
        source, target, value = self._get_filter_links()

        if source is None:
            return None

        return self._plot(source, target, value)

    def plot_div(self):
        """
        Generate a div containing the Sankey diagram.

        """
        source, target, value = self._get_filter_links()

        if source is None:
            return None

        fig = self._plot(source, target, value)

        # Getting HTML needed to render the plot.
        return plot(fig, output_type="div")

    def _get_filter_links(self):
        source = []
        target = []
        value = []

        for dataset in self.datasets:
            # loop round all of the dataset(s)
            # this could be all datasets for a URL, all CS3 datasets or all CCI datasets

            for relationship in dataset.relationship_set.all():
                # now loop round all of the relationships for this dataset
                source_index = self._get_index(
                    dataset.url, f"Dataset: {dataset}", SANKEY_COLOUR_1
                )
                last_colour = SANKEY_COLOUR_1.replace("1.0", SANKEY_FADE)

                if len(dataset.filters.all()) == 0:
                    # No filters on the prime datasets
                    related_ds = relationship.to_dataset
                    if len(related_ds.filters.all()) > 0:
                        filter_index = self._add_filters(
                            related_ds,
                            source_index,
                            source,
                            target,
                            value,
                            last_colour,
                            relationship,
                        )
                    else:
                        filter_index = source_index

                    target_index = self._get_index(
                        related_ds.url, f"Dataset: {related_ds}", SANKEY_COLOUR_1
                    )
                    source.append(filter_index)
                    target.append(target_index)
                    value.append(1)
                    self.link_colours.append(last_colour)
                    self.link_names.append(str(relationship))

                else:
                    # Filters on the prime datasets
                    primary_filter_index = self._add_filters(
                        dataset,
                        source_index,
                        source,
                        target,
                        value,
                        last_colour,
                        relationship,
                    )

                    related_ds = relationship.to_dataset

                    if len(related_ds.filters.all()) > 0:
                        filter_index = self._add_filters(
                            related_ds,
                            primary_filter_index,
                            source,
                            target,
                            value,
                            last_colour,
                            relationship,
                        )
                    else:
                        filter_index = primary_filter_index

                    target_index = self._get_index(
                        related_ds.url, f"Dataset: {related_ds}"
                    )
                    source.append(filter_index)
                    target.append(target_index)
                    value.append(1)
                    self.link_colours.append(last_colour)
                    self.link_names.append(str(relationship))

        return source, target, value

    def _add_filters(
        self, dataset, source_index, source, target, value, last_colour, relationship
    ):
        # we need to include the filters in the diagram
        # filter_indecies = []
        first_index = source_index

        # get the filters for the dataset
        filters = list(dataset.filters.all())
        filters.sort(key=_filter_sorter)

        for filter_ in filters:
            if filter_.name in [
                "processinglevel",
                "processing_level",
                "origin",
            ]:
                colour = SANKEY_COLOUR_2
            elif filter_.name == "version":
                colour = SANKEY_COLOUR_3
            elif filter_.name.startswith("sensor"):
                colour = SANKEY_COLOUR_4
            elif filter_.name == "variable":
                colour = SANKEY_COLOUR_5
            elif filter_.name.startswith("algorithm") or filter_.name.startswith(
                "projection"
            ):
                colour = SANKEY_COLOUR_6
            else:
                colour = SANKEY_COLOUR_7

            filter_index = self._get_index(
                str(filter_),
                f"Dataset filter: {filter_}",
                colour,
                first_index,
            )
            # filter_indecies.append(filter_index)

            source.append(first_index)
            target.append(filter_index)
            value.append(1)

            self.link_colours.append(last_colour)
            last_colour = colour.replace("1.0", SANKEY_FADE)
            self.link_names.append(str(relationship))
            first_index = filter_index

        return first_index

    # , source, target, value, last_colour

    def _get_index(self, value, node_name, colour=None, source_entity=None):
        """
        Get the index for a given value.

        If this is a new value then store some information about this value,
        otherwise store information about the link.

        @param value(str): this may be a dataset URL or filter name

        @param source_entity(str): the id of the starting entity for a link

        """
        # do we already have a node for this value?
        id_ = self.nodes.get(value)

        if id_ is not None:
            return id_

        if source_entity is not None:
            id_ = self.links.get(f"{source_entity}-{value}")
            if id_ is not None:
                return id_

        self.last_id += 1
        self.node_names[self.last_id] = node_name

        if source_entity is not None:
            self.duplicates[self.last_id] = value
            self.links[f"{source_entity}-{value}"] = self.last_id

        else:
            self.nodes[value] = self.last_id

        if colour is not None:
            self.node_colours[self.last_id] = colour
        else:
            self.node_colours[self.last_id] = SANKEY_COLOUR_7

        return self.last_id

    def _plot(self, source, target, value):
        ivd = {v: k for k, v in self.nodes.items()}
        ivd.update(self.duplicates)
        keys = sorted(ivd.keys())
        labels = []
        colours = []
        node_names = []
        for key in keys:
            labels.append(ivd[key])
            colours.append(self.node_colours[key])
            node_names.append(self.node_names[key])

        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=15,
                        thickness=20,
                        line=dict(color="black", width=0.5),
                        label=labels,
                        color=colours,
                        customdata=node_names,
                        hovertemplate="%{customdata}<extra></extra>",
                    ),
                    link=dict(
                        source=source,
                        target=target,
                        value=value,
                        color=self.link_colours,
                        customdata=self.link_names,
                        hovertemplate="%{customdata}<extra></extra>",
                    ),
                )
            ]
        )

        font_size = 11
        if len(source) < 10:
            height = 300
        elif len(source) < 20:
            height = 400
        elif len(source) < 40:
            height = 600
        elif len(source) < 80:
            height = 800
        elif len(source) < 120:
            font_size = 10
            height = 1500
        elif len(source) < 200:
            font_size = 10
            height = 2000
        else:
            font_size = 10
            height = 3000

        fig.update_layout(
            title_text=self.title,
            font_size=font_size,
            height=height,
        )
        return fig


def _filter_sorter(filter_):
    if filter_.name == "origin":
        return 1
    if filter_.name in ["processinglevel", "processing_level"]:
        return 2
    if filter_.name == "version":
        return 3
    if filter_.name.startswith("sensor"):
        return 4
    if filter_.name == "variable":
        return 5
    if filter_.name.startswith("algorithm"):
        return 6
    if filter_.name.startswith("projection"):
        return 7
    return 8


def _fix_url(url):
    if "http://" not in url and "https://" not in url:
        # fix URL
        url = url.replace("http:/", "http://")
        url = url.replace("https:/", "https://")
    return url
