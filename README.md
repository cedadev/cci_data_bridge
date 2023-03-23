# CCI Data Bridge

The CCI Data Bridge provides a means of linking together related datasets from different projects, currently CCI and C3S.

The datasets are linked together via one or more relationships.

In most cases it is not as simple as one dataset relating directly to another dataset, there can be many reasons for this. Hence the use of filters. One or more filters can be used to narrow down the portion of the dataset that is involved in the relationship.

User documentation for the [API](https://cedadev.github.io/cci_data_bridge/) has been generated from an [Open API yaml](cci_data_bridge/static/cci_data_bridge/openAPI.yaml) file.

An [entity relationship diagram](docs/erd.png) shows the structure of the tables in the database that is used to store the information about the relationships.
