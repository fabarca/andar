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

    :param path_template: String. Path template that follows string.Formatter() syntax.
    :return: List. Template fields names.
    """
    parsed_field_tuples = list(string.Formatter().parse(path_template))
    template_fields_names = [name for (text, name, spec, conv) in parsed_field_tuples if name is not None]
    return template_fields_names


def assign_groupname_pattern_dict(pattern_dict: dict[str:str]) -> dict[str:str]:
    """
    Assign a group name to each regex pattern present in the given dictionary

    :param pattern_dict: A dictionary of regex patterns, where each key will be used as group name. It does not
                            check if the pattern already have a group name assign.
    :return: A dictionary where the patterns have been assigned a group name.
    """
    named_pattern_dict = {}
    for field, pattern in pattern_dict.items():
        named_pattern_dict[field] = f"(?P<{field}>{pattern})"
    return named_pattern_dict


def parse_fields(
    _string: str,
    template: str,
    pattern_dict: dict[str:str],
    raise_error: bool = False,
) -> dict[str:str]:
    """
    Parse a string using a template and a patterns dictionary

    Example:
    filename_template = "{prefix}_{name}.{extension}"
    pattern_dict = {"prefix": "[0-9]{4}", "name": "[a-zA-Z0-9]+", "extension": "json"}
    filename = "0001_example.json"
    parsed_filename_dict = parse_fields(filename, filename_template, pattern_dict)
    invalid_filename = "invalid_example.json"
    parse_fields(invalid_filename, filename_template, pattern_dict, raise_error=True)

    :param _string: String to be parsed.
    :param template: A template that follows string.Formatter() syntax.
    :param pattern_dict: A dictionary where each key represent a field of the template and each value is the
                            corresponding regex pattern
    :param raise_error: Raise an exception if the path is not valid. If False, it returns None.
    :return: A dictionary of parsed fields.
    """
    template_field_names = get_template_fields_names(template)
    pattern_field_names = list(pattern_dict.keys())
    check_expected_fields(template_field_names, pattern_field_names)

    # Deduplicate repeated fields of pattern_dict:
    # for example the template "/{base_path}/{asset_name}/{asset_name}_{suffix}"
    # will become "/{base_path}/{asset_name__0}/{asset_name__1}_{suffix}"
    # and the dict {"base_path": r"\w+", "asset_name": r"\w+", "suffix": r"\d+"}
    # will become {"base_path": r"\w+", "asset_name__0": r"\w+", "asset_name__1": r"\w+", "suffix": r"\d+"}
    unique_fields = list(set(template_field_names))
    deduplicated_fields_dict = {}
    new_pattern_dict = {}
    new_template = template
    for field_name in unique_fields:
        field_count = len([f for f in template_field_names if f == field_name])
        if field_count == 1:
            new_pattern_dict[field_name] = pattern_dict[field_name]
            continue
        deduplicated_list = []
        for idx in range(field_count):
            new_field_name = field_name + f"__{idx}"
            deduplicated_list.append(new_field_name)
            new_pattern_dict[new_field_name] = pattern_dict[field_name]
            new_template = new_template.replace("{" + field_name + "}", "{" + new_field_name + "}", 1)
        deduplicated_fields_dict[field_name] = deduplicated_list

    has_duplicates = pattern_dict != new_pattern_dict
    if has_duplicates:
        pattern_dict = new_pattern_dict
        template = new_template

    # Build full pattern string
    named_pattern_dict = assign_groupname_pattern_dict(pattern_dict)
    path_pattern = template.format(**named_pattern_dict)
    path_pattern = f"^{path_pattern}$"  # match the full string
    match = re.match(path_pattern, _string)
    if not match:
        if raise_error:
            raise ValueError(f"Invalid string '{_string}', expected pattern: '{path_pattern}'")
        return None
    parsed_fields_dict = match.groupdict()

    # Fusion deduplicated fields:
    # it will raise an error if the deduplicate fields have multiples values
    # for example this parsed dict will raise an error because asset_name__0 and asset_name__1 should be equal:
    # {"base_path": "folder", "asset_name__0": "my_asset", "asset_name__1": "other_asset", "suffix": "001"}
    # if the deduplicated fields are coherent they will be fusion and renamed to its original name:
    # for example {"base_path": "folder", "asset_name__0": "my_asset", "asset_name__1": "my_asset", "suffix": "001"}
    # to {"base_path": "folder", "asset_name": "my_asset", "suffix": "001"}
    for original_field_name, deduplicated_list in deduplicated_fields_dict.items():
        parsed_field_values = [parsed_fields_dict.pop(f) for f in deduplicated_list]
        unique_parsed_field_values = list(set(parsed_field_values))
        are_duplicated_unique = len(unique_parsed_field_values) == 1
        if not are_duplicated_unique:
            raise ValueError(
                f"More than one value was found for repeated field '{original_field_name}': {parsed_field_values}"
            )
        parsed_fields_dict[original_field_name] = unique_parsed_field_values[0]

    return parsed_fields_dict


def prepare_fields_values(fields_values_dict: dict[str:Any], fields_conf: dict[str, FieldConf]) -> dict[str:str]:
    """
    Prepare fields values for this path
    :param fields_values_dict: Dictionary of fields values
    :param fields_conf: Dictionary of fields configuration (i.e.class FieldConf)
    :return: A dictionary of fields where the values were converted to strings.
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


def process_parsed_fields_values(fields_conf: dict[str, FieldConf], parsed_fields: dict[str:str]) -> dict[str:Any]:
    """
    Process fields values dictionary obtained from parsing a file path

    :param parsed_fields: A dictionary of parsed fields values in string format.
    :return: A processed dictionary of fields with converted values depending on each FieldConf definition.
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
