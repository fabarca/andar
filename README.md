# Andar Package

> *Caminante, no hay camino, se hace camino al **andar**.*
> 
> Antonio Machado

Andar is a python package that provides an abstraction layer for managing path structures, helping to create and parse paths in a programmatic way via templated file paths.


## Install Package

With pip:
```bash
pip install andar
```


## Quick start:

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
    template="/{base_path}/{subfolder}/{date_path}/{date_prefix}_{name}_{datetime_suffix}.{ext}",
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

base_path = "company/reports"
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

## Documentation
See the [official documentation](https://fabarca.github.io/andar) to learn more.
