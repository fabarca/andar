from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Self


class SafePatterns:
    """
    Non-greedy patterns

    Attributes:
        FIELD: Alphanumeric characters
        NAME: Alphanumeric characters plus name separators: `-_.`
        DIRPATH: Alphanumeric characters plus name separators: `-_.` plus directory separator: `/`
        EXTENSION: Alphanumeric characters plus dots for sub extensions as in `tar.gz`
    """

    FIELD = r"[a-zA-Z0-9]+?"  # without separator characters
    NAME = r"[-_.a-zA-Z0-9]+?"  # include name separators: -_.
    DIRPATH = r"[-_.a-zA-Z0-9/]+?"  # include name separators: -_. and directory separator: /
    EXTENSION = r"[.a-zA-Z0-9]+?"  # include dots for sub extensions as 'tar.gz'


@dataclass
class FieldConf:
    """
    FieldConf allows to configure how a path field is validated, parsed and processed

    Params:
        pattern: Regex pattern used to validate the input of get_path and get_parent_path, and also to get fields
                 using PathModel.parse_path(). By default, it used SafePatterns.NAME.
        description: String used as documentation for the FieldConf.
        date_format: date_format and datetime_format are used in get_path and get_parent_path for accepting either a
                        string or a datetime object that can be formated to an input string for a the given template.
                        They are also used for validating the parsed field when using parse_path and for defining how
                        to cast the string (to date or to datetime, depending on the argument that was used).
        datetime_format: See description of date_format parameter.
        is_optional: allows to omit a field during the path generation (get_path and get_parent_path)
                        or to skip field during the path parsing. IMPORTANT! in order to work properly, pattern must
                        be constrained, otherwise the PathModel class may have an unexpected behaviour.
                        For example use '[0-9]{4}' and avoid using '*' or '+' when using is_optional=True.
    """

    pattern: str = SafePatterns.NAME
    description: str | None = None
    date_format: str | None = None
    datetime_format: str | None = None
    is_optional: bool | None = None
    str_to_var: Callable | None = None
    var_to_str: Callable | None = None

    def __post_init__(self):
        has_date_converter = self.date_format is not None
        has_datetime_converter = self.datetime_format is not None
        has_custom_converter = self.var_to_str is not None or self.str_to_var is not None
        active_converters_num = sum([has_date_converter, has_datetime_converter, has_custom_converter])
        if active_converters_num > 1:
            raise ValueError(f"Maximum one field converter is allowed, but {active_converters_num} were found")

    def __repr__(self):
        formatted_fields = []
        for k, v in vars(self).items():
            if v is None:
                continue
            v_str = f"'{v}'" if isinstance(v, str) else v.__qualname__
            field_str = f"{k}={v_str}"
            formatted_fields.append(field_str)
        formatted_fields_str = ", ".join(formatted_fields)
        repr = f"FieldConf({formatted_fields_str})"
        return repr

    def replace(self, **kwargs: Any) -> Self:
        """
        Creates a copy of the current object replacing attributes with the given keyword arguments

        Params:
            **kwargs: Attributes (parameters) to be replaced

        Returns:
            A copy of the object with the attributes replaced
        """
        field_conf = replace(self, **kwargs)
        return field_conf
