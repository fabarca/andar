# Welcome to Andar Docs


Andar module implement a PathBuilder class that allows to define, create and parse templated paths.

## Project Overview


## Example usage:

```python
from andar import PathBuilder

# Simple definition, using automatic definition of fields
simple_path_builder = PathBuilder(template="{base_folder}/{intermediate_folder}/{base_name}_{suffix}.{extension}")

result_path = simple_path_builder.get_path(
    base_folder="parent_folder",
    intermediate_folder="other_folder",
    base_name="mydata",
    suffix="2000-01-01",
    extension="csv",
)
print(result_path)  # "parent_folder/other_folder/mydata_2000-01-01.csv"

result_parent_path = simple_path_builder.get_parent_path(
    base_folder="parent_folder",
    intermediate_folder="other_folder",
)
print(result_parent_path)  # "parent_folder/other_folder"

file_path = "parent_folder/other_folder/mydata_2000-01-01.csv"
parsed_fields = simple_path_builder.parse_file_path(file_path)
print(parsed_fields)

```

