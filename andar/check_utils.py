def check_expected_fields(expected_field_names: list[str], new_field_names: list[str]) -> None:
    """
    Check if fields in the expected_field_names are coherent with new_field_names

    Params:
        expected_field_names: The expected list of field names.
        new_field_names: The new list of field names to be validated.
    """
    invalid_fields = [f for f in new_field_names if f not in expected_field_names]
    if invalid_fields:
        raise ValueError(
            f"Invalid fields: {invalid_fields} they do not exist in expected field list: '{expected_field_names}'"
        )

    missing_fields = [f for f in expected_field_names if f not in new_field_names]
    if missing_fields:
        raise ValueError(
            f"Missing fields: {missing_fields} they are required in expected field list: '{expected_field_names}'"
        )


def check_parent_path_template(path_template: str, parent_path_template: str) -> None:
    """
    Check if parent_path_template is coherent with path_template

    Params:
        path_template: String. Path template that follows string.Formatter() syntax.
        parent_path_template: String. Parent path template that follows string.Formatter() syntax.
    """
    if parent_path_template not in path_template:
        raise ValueError(
            f"path_template: '{path_template}' does not match with parent_path_template: "
            f"'{parent_path_template}'. parent_path_template must be a substring of path_template"
        )
