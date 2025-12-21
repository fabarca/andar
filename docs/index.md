# Welcome to Andar Docs


Andar package implements a PathModel class that allows to define, build and parse templated file paths.

## Project Overview


## Example usage:

```python
from andar import PathModel

# Simple definition, using automatic definition of fields
simple_path_model = PathModel(template="/{base_folder}/{subfolder}/{base_name}__{suffix}.{extension}")

# Generate a path:
result_path = simple_path_model.get_path(
    base_folder="parent_folder",
    subfolder="other_folder",
    base_name="mydata",
    suffix="2000-01-01",
    extension="csv",
)
print(result_path)
# Result:
# "/parent_folder/other_folder/mydata__2000-01-01.csv"

# Parse a path:
file_path = "/data/reports/summary__2025-12-31.csv"
parsed_fields = simple_path_model.parse_path(file_path)
print(parsed_fields)

# Result:
# {
#     'base_folder': 'data', 
#     'subfolder': 'reports', 
#     'base_name': 'summary', 
#     'suffix': '2025-12-31', 
#     'extension': 'csv',
# }

```

