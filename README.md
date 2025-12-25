# Andar Package

> *Caminante, no hay camino, se hace camino al **andar**.*
> 
> Antonio Machado

Andar is a python package that provides an abstraction layer for managing path structures, helping to create paths and parse them in a programatic way via templated file paths.


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

## Next steps
See the [official documentation](https://fabarca.github.io/andar) to learn more.
