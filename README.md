# Andar Package

Andar is a Python library that provides an abstraction layer for managing path structures, helping to create and parse paths programmatically via templated file paths.


## Install Package

With pip:
```bash
pip install andar
```

## Key features

### Clean code

Andar promotes clean code by using a composition approach to avoid inheritance hell.
Furthermore, it allows to define a path conventions in a single place using a clear and intuitive syntax.
The use of templated path strings with field definitions helps to avoid the error-prone split/index syntax

### Reusability

Andar allows using a single path convention via a PathModel for both generating and parsing paths.
PathModels can be reused to create new path conventions with minimal effort without modifying the parent PathModel.

### Separation of Concerns

Andar helps to separate I/O layer from path generation layer resulting in a code easier to maintain.

### Predictability

Andar provides field name checking via regular expressions and functions to assert bijection between path generation and
path parsing.

### Flexibility

Andar allows for a quick start just by defining a path template thanks to its predefined fields and patterns. It also 
include more advance capabilities for customizing field parsing and generation via regular expression and string converters while 
maintaining a simple syntax.

### Lightweight

Andar is written using standard Python library, so it is very lightweight without any external dependencies.

## Concepts

### PathModel

PathModel is the main class that allows to easy define path conventions and manage path structures. It is based on two
main components: templates and fields.
Templates are strings that define the names of the fields in the path structure using a simple syntax 
(inspired by f-string) , for example: `"/{folder}/{prefix}_{name}_{suffix}.{ext}"`
Fields are the basic components that allow to map an object to a string in order to build or parse a path. Fields 
are defined via a class named FieldConf (see next section).

A PathModel can be defined only with the template string because there is already a default value for fields.
Once a PathModel is defined it can be used to generate a new path or to parse an existing path in order to get 
its fields. See [Quick Start](#quick-start) for a simple example. For more details check the [Docs](https://fabarca.github.io/andar/reference/andar/path_model/).


### FieldConf

FieldConf is the class that defines how to parse and build a given field. It can be customized by specifying its regex pattern and how to convert the input object to a string and vice versa. It comes with a handy way for automatically manage dates and datetimes. See [Examples](#examples) section for some applied use cases. For more details check the [Docs](https://fabarca.github.io/andar/reference/andar/field_conf/).


## Quick Start

Simple PathModel definition using default field configurations:

```python
from andar import PathModel

simple_path_model = PathModel(
    template="/{base_folder}/{subfolder}/{base_name}__{suffix}.{extension}"
)
```

Generate a path:

```python
result_path = simple_path_model.get_path(
    base_folder="parent_folder",
    subfolder="other_folder",
    base_name="mydata",
    suffix="2000-01-01",
    extension="csv",
)
print(result_path)
```

```python
"/parent_folder/other_folder/mydata__2000-01-01.csv"
```

Parse a path:

```python
file_path = "/data/reports/summary__2025-12-31.csv"
parsed_fields = simple_path_model.parse_path(file_path)
print(parsed_fields)
```

```python
{
    'base_folder': 'data', 
    'subfolder': 'reports', 
    'base_name': 'summary', 
    'suffix': '2025-12-31', 
    'extension': 'csv',
}
```

## Examples

### How to create a path generator / parser for a date tree structure

Define a PathModel following a date tree folder structure with datetime a suffix using the next template and fields:

```python
from andar import FieldConf, PathModel, SafePatterns

date_archived_pm = PathModel(
    template="{base_path}/{subfolder}/{date_path}/{date_prefix}_{name}_{datetime_suffix}.{ext}",
    fields={
        "base_path": FieldConf(pattern=SafePatterns.DIRPATH),
        "subfolder": FieldConf(pattern=SafePatterns.NAME),
        "date_path": FieldConf(pattern=r"\d{4}/\d{2}/\d{2}", date_format="%Y/%m/%d"),
        "date_prefix": FieldConf(pattern=r"\d{4}-\d{2}-\d{2}", date_format="%Y-%m-%d"),
        "name": FieldConf(pattern=SafePatterns.FIELD),
        "datetime_suffix": FieldConf(pattern=r"\d{8}_\d{6}", datetime_format="%Y%m%d_%H%M%S"),
        "ext": FieldConf(pattern=SafePatterns.EXTENSION),
    },
)
```

Then, for generating the paths just iterate over dates:

```python
import datetime as dt

base_path = "/company/reports"
subfolder = "finance"
report_name = "revenue"
extension = "xls"
start_date = dt.date(2025, 12, 1)
report_date_list = [start_date + dt.timedelta(days=d) for d in range(10)]

for report_date in report_date_list:
    creation_datetime = dt.datetime.now()
    report_path = date_archived_pm.get_path(
        base_path=base_path,
        subfolder=subfolder,
        date_path=report_date,
        date_prefix=report_date,
        name=report_name,
        datetime_suffix=creation_datetime,
        ext=extension,
    )
    print(report_path)
```

For parsing already existing paths use a library that allows to recursive search (e.g. pathlib, glob, os, etc) 
and output a fullpath for each file:

```python
import pathlib
base_path = "/company/reports"
search_folder = pathlib.Path(base_path)
path_list = [str(i) for i in search_folder.rglob("*") if i.is_file()]

for file_path in path_list:
    parsed_fields = date_archived_pm.parse_path(file_path)
    print(parsed_fields)

```

### How to define path conventions for a datalake

For example Data Mesh propose conventions for separating data into domains, layers and products. 
This could be implemented with the following PathModel template and fields:

```python
from andar import FieldConf, PathModel, SafePatterns

data_mesh_pm = PathModel(
    template="/{domain}/{layer}/{product}/{aggregation}/{date}_{product}.{ext}",
    fields={
        "domain": FieldConf(pattern=SafePatterns.NAME),  # sales, marketing, HR, finance, etc
        "layer": FieldConf(pattern=SafePatterns.NAME),  # raw, intermediate, mart, etc
        "product": FieldConf(pattern=SafePatterns.NAME),  # orders, revenues, taxes, campaigns, etc
        "aggregation": FieldConf(pattern=SafePatterns.NAME),  # daily, weekly, monthly, etc
        "date": FieldConf(pattern=r"\d{8}", datetime_format="%Y%m%d"),  # product date
        "ext": FieldConf(pattern=SafePatterns.EXTENSION),  # csv, xls, parquet, etc
    },
)
```

For improving traceability, it's a good practice to also include run datetime (i.e. generation date) 
as a simple version system:
```python
from andar import FieldConf, PathModel, SafePatterns

data_mesh_pm = PathModel(
    template="/{domain}/{layer}/{product}/{aggregation}/{product_date}_{product}_{run_datetime}.{ext}",
    fields={
        "domain": FieldConf(pattern=SafePatterns.NAME),  # sales, marketing, HR, finance, etc
        "layer": FieldConf(pattern=SafePatterns.NAME),  # raw, intermediate, mart, etc
        "product": FieldConf(pattern=SafePatterns.NAME),  # orders, revenues, taxes, campaigns, etc
        "aggregation": FieldConf(pattern=SafePatterns.NAME),  # daily, weekly, monthly, etc
        "product_date": FieldConf(pattern=r"\d{8}", datetime_format="%Y%m%d"),  # product target date
        "run_datetime": FieldConf(pattern=r"\d{8}_\d{6}", datetime_format="%Y%m%d_%H%M%S"),  # generation datetime
        "ext": FieldConf(pattern=SafePatterns.EXTENSION),  # csv, xls, parquet, etc
    },
)
```


### How to reorganize files and folders in a datalake

In this example we will reorganize a flatten file structure into a nested one.
First define the two PathModels, the old one and the new one:

```python
from andar import FieldConf, PathModel, SafePatterns

old_flat_pm = PathModel(
    template="{base_path}/{category}_{name}_{date}.{ext}",
    fields={
        "base_path": FieldConf(pattern=SafePatterns.DIRPATH),
        "category": FieldConf(pattern=SafePatterns.NAME),
        "name": FieldConf(pattern=SafePatterns.FIELD),
        "date": FieldConf(pattern=r"\d{8}", datetime_format="%Y%m%d"),
        "ext": FieldConf(pattern=SafePatterns.EXTENSION),
    },
)

# we can just update the template if the fields are de same
new_nested_pm = old_flat_pm.update(
    template="{base_path}/{category}/{date}/{name}.{ext}"
)
```

Example of file creating in a temporary directory using a flatten structure with the old PathModel:

```python
import pathlib
import tempfile
import datetime as dt

base_path = tempfile.mkdtemp()
start_date = dt.datetime(2025, 12, 1)
date_list = [start_date + dt.timedelta(days=d) for d in range(10)]

for date in date_list:
    creation_datetime = dt.datetime.now()
    file_path = old_flat_pm.get_path(
        base_path=base_path,
        category="sales",
        name="orders",
        date=date,
        ext="csv",
    )
    print(file_path)
    pathlib.Path(file_path).touch()  # create an empty file
```

Example of nesting file paths using the parser of the old PathModel and the get_path of the new PathModel:

```python
# First list existing files in target base path
search_folder = pathlib.Path(base_path)
path_list = [str(i) for i in search_folder.rglob("*") if i.is_file()]

for file_path in path_list:
    parsed_fields = old_flat_pm.parse_path(file_path)
    # As the fields are the same we can reuse them directly
    new_file_path = new_nested_pm.get_path(**parsed_fields)
    # create new parent directories
    pathlib.Path(new_file_path).parent.mkdir(parents=True, exist_ok=True)
    # move old file to new location using the new name
    pathlib.Path(file_path).replace(new_file_path)
```

The same strategy could be adapted to flatten a nested path structure using PathModels.

## Documentation
See the [official documentation](https://fabarca.github.io/andar) to learn more.


## Package name origin

The package name originates from a verse by the Spanish poet Antonio Machado:
> "Caminante, no hay camino, se hace camino al **andar**."
> 
> Antonio Machado
