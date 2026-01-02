"""
Module containing utility functions
"""

import datetime as dt
import re
import string
from typing import Any

from andar.check_utils import check_expected_fields
from andar.field_conf import FieldConf


def get_template_fields_names(path_template: str) -> list[str]:
    """
    Get fields names from path template string

    Params:
        path_template: Path template that follows string.Formatter() syntax.

    Returns:
        Template fields names.
    """
    parsed_field_tuples = list(string.Formatter().parse(path_template))
    template_fields_names = [name for (text, name, spec, conv) in parsed_field_tuples if name is not None]
    return template_fields_names


def assign_groupname_pattern_dict(pattern_dict: dict[str:str]) -> dict[str:str]:
    """
    Assign a group name to each regex pattern present in the given dictionary

    Params:
        pattern_dict: A dictionary of regex patterns, where each key will be used as group name. It does not
                  check if the pattern already have a group name assign.

    Returns:
        A dictionary where the patterns have been assigned a group name.
    """
    named_pattern_dict = {}
    for field, pattern in pattern_dict.items():
        named_pattern_dict[field] = f"(?P<{field}>{pattern})"
    return named_pattern_dict


def compile_path_regex(template: str, fields: dict[str:FieldConf], ds: str = "/") -> re.Pattern:
    """
    Compile a regex pattern using a path template and a FieldConf dictionary

    Example:
        ```python
        filename_template = "{prefix}_{name}.{extension}"
        fields = {
            "prefix": FieldConf(pattern=r"[0-9]{4}"),
            "name": FieldConf(pattern=r"[a-zA-Z0-9]+"),
            "extension": FieldConf(pattern=r"json")
        }
        filename = "0001_example.json"
        compiled_regex = compile_path_regex(filename_template, fields)
        compiled_regex.match(filename).groupdict()
        ```

    Params:
        template: A path template that follows `PathModel.template` syntax.
        fields: A dictionary where each key represent a field of the template and each value represent its corresponding
                `FieldConf()`.
        ds: Directory separator string.

    Returns:
        A compiled regex pattern.
    """
    template_field_names = get_template_fields_names(template)
    field_names = list(fields.keys())
    check_expected_fields(template_field_names, field_names)

    invalid_fields = [n for n in field_names if n.find("__") >= 0]

    if len(invalid_fields) > 0:
        raise ValueError(f"Fields cannot contains double underscore: {invalid_fields}")

    template = template.replace(r".", r"\.")
    pattern_dict = {}
    for field_name, field_conf in fields.items():
        field_pattern = field_conf.pattern
        if field_conf.is_optional:
            field_pattern = f"{field_pattern}|"
            # Allow optional directory separator for this field: "/" -> "/?", by updating path_template
            field_name_dir_sep = "{" + field_name + "}" + ds + "{"
            optional_field_name_dir_sep = "{" + field_name + "}" + ds + "?{"
            template = template.replace(field_name_dir_sep, optional_field_name_dir_sep)
        pattern_dict[field_name] = field_pattern

    # Deduplicate repeated fields of pattern_dict:
    # for example the template "{base_path}/{asset_name}/{asset_name}_{suffix}"
    # will become "{base_path}/{asset_name__0}/{asset_name__1}_{suffix}"
    # and the dict {"base_path": r"\w+", "asset_name": r"\w+", "suffix": r"\d+"}
    # will become {"base_path": r"\w+", "asset_name__0": r"\w+", "asset_name__1": r"\w+", "suffix": r"\d+"}
    unique_fields = list(set(template_field_names))
    new_pattern_dict = {}
    new_template = template
    for field_name in unique_fields:
        field_count = len([f for f in template_field_names if f == field_name])
        if field_count == 1:
            new_pattern_dict[field_name] = pattern_dict[field_name]
            continue
        for idx in range(field_count):
            new_field_name = field_name + f"__{idx}"
            new_pattern_dict[new_field_name] = pattern_dict[field_name]
            new_template = new_template.replace("{" + field_name + "}", "{" + new_field_name + "}", 1)

    has_duplicates = pattern_dict != new_pattern_dict
    if has_duplicates:
        pattern_dict = new_pattern_dict
        template = new_template

    # Build full pattern string
    named_pattern_dict = assign_groupname_pattern_dict(pattern_dict)
    path_pattern = template.format(**named_pattern_dict)
    path_pattern = f"^{path_pattern}$"  # match the full string
    compiled_pattern = re.compile(path_pattern)
    return compiled_pattern


def fusion_deduplicated_fields(parsed_field_dict: dict[str, str]) -> dict[str, str]:
    """
    Fusion deduplicated fields in a parsed field dict

    Example:
        ```python
        deduplicated_field_dict = {
            "name": "data",
            "version__0": "v1",
            "version__1": "v1",
            "ext": "csv",
        }
        fusioned_field_dict = fusion_deduplicated_fields(deduplicated_field_dict)
        # {
        #     "name": "data",
        #     "version": "v1",
        #     "ext": "csv",
        # }
        ```

    Params:
        parsed_field_dict: A dictionary where each key represent a field name. A deduplicated field will have a
                           suffix `__{id}`.

    Returns:
        A dictionary where deduplicated fields are fusioned in a single field with the suffix removed.
    """

    deduplicated_regex = re.compile(r"^(?P<name>.+?)__(?P<id>\d)$")

    deduplicated_fields_dict = {}

    for field_name in parsed_field_dict:
        match = deduplicated_regex.match(field_name)
        if match is None:
            continue
        match_dict = match.groupdict()
        original_field_name = match_dict["name"]
        if original_field_name not in deduplicated_fields_dict:
            deduplicated_fields_dict[original_field_name] = []
        deduplicated_fields_dict[original_field_name].append(field_name)

    # Fusion deduplicated fields:
    # it will raise an error if the deduplicate fields have multiples values
    # for example this parsed dict will raise an error because asset_name__0 and asset_name__1 should be equal:
    # {"base_path": "folder", "asset_name__0": "my_asset", "asset_name__1": "other_asset", "suffix": "001"}
    # if the deduplicated fields are coherent they will be fusion and renamed to its original name:
    # for example {"base_path": "folder", "asset_name__0": "my_asset", "asset_name__1": "my_asset", "suffix": "001"}
    # to {"base_path": "folder", "asset_name": "my_asset", "suffix": "001"}
    for original_field_name, deduplicated_list in deduplicated_fields_dict.items():
        parsed_field_values = [parsed_field_dict.pop(f) for f in deduplicated_list]
        unique_parsed_field_values = list(set(parsed_field_values))
        are_duplicated_unique = len(unique_parsed_field_values) == 1
        if not are_duplicated_unique:
            raise ValueError(
                f"More than one value was found for repeated field '{original_field_name}': {parsed_field_values}"
            )
        parsed_field_dict[original_field_name] = unique_parsed_field_values[0]
    return parsed_field_dict


def prepare_fields_values(fields_values_dict: dict[str, Any], fields_conf: dict[str, FieldConf]) -> dict[str, str]:
    """
    Prepare fields values for this path

    Params:
        fields_values_dict: Dictionary of fields values
        fields_conf: Dictionary of fields configuration (i.e.class FieldConf)

    Returns:
        A dictionary of fields where the values were converted to strings.
    """
    new_fields_values_dict = {}
    for field_name, field_value in fields_values_dict.items():
        if field_name not in fields_conf:
            print(f"skipping field '{field_name}'")
            continue
        field_conf = fields_conf[field_name]

        if field_value is None and field_conf.is_optional:
            new_fields_values_dict[field_name] = ""
            continue

        if field_conf.date_format is not None:
            new_field_value = field_value.strftime(field_conf.date_format)
        elif field_conf.datetime_format is not None:
            new_field_value = field_value.strftime(field_conf.datetime_format)
        elif field_conf.var_to_str is not None:
            new_field_value = field_conf.var_to_str(field_value)
        else:
            new_field_value = str(field_value)

        field_pattern = f"^{field_conf.pattern}$"  # Exact pattern
        result = re.match(field_pattern, new_field_value)
        if result is None:
            raise ValueError(
                f"Invalid field '{field_name}' value: '{new_field_value}'. It does not match pattern: "
                f"'{field_conf.pattern}'"
            )
        new_fields_values_dict[field_name] = new_field_value
    return new_fields_values_dict


def process_parsed_fields_values(fields_conf: dict[str, FieldConf], parsed_fields: dict[str, str]) -> dict[str, Any]:
    """
    Process fields values dictionary obtained from parsing a file path

    Params:
        parsed_fields: A dictionary of parsed fields values in string format.

    Returns:
        A processed dictionary of fields with converted values depending on each FieldConf definition.
    """
    new_parsed_fields = parsed_fields.copy()

    for field_name, field_value in new_parsed_fields.items():
        if field_name not in fields_conf:
            raise ValueError(f"Unknown field '{field_name}'. Valid fields are: {fields_conf.keys()}")
        field_conf = fields_conf[field_name]

        field_pattern = f"^{field_conf.pattern}$"  # Exact pattern
        if field_conf.is_optional:
            field_pattern = f"^{field_conf.pattern}|$"
        result = re.match(field_pattern, field_value)
        if result is None:
            raise ValueError(
                f"Invalid field '{field_name}' value: '{field_value}'. It does not match pattern: "
                f"'{field_conf.pattern}'"
            )

        if field_conf.date_format is not None:
            new_field_value = dt.datetime.strptime(field_value, field_conf.date_format).date()
        elif field_conf.datetime_format is not None:
            new_field_value = dt.datetime.strptime(field_value, field_conf.datetime_format)
        elif field_conf.str_to_var is not None:
            new_field_value = field_conf.str_to_var(field_value)
        else:
            new_field_value = str(field_value)

        if new_field_value == "" and field_conf.is_optional:
            new_field_value = None

        new_parsed_fields[field_name] = new_field_value
    return new_parsed_fields
