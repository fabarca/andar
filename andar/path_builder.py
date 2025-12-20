import datetime as dt
import os.path
import re
import string
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from typing_extensions import Self


class SafePatterns:
    """
    Non-greedy patterns
    """

    FILENAME = r"[-_.a-zA-Z0-9]+?"  # include filename separators: -_.
    DIRPATH = r"[-_.a-zA-Z0-9/]+?"  # include filename separators: -_. and directory separator: /
    FIELD = r"[a-zA-Z0-9]+?"  # without separator characters
    EXTENSION = r"[.a-zA-Z0-9]+?"  # include dots for sub extensions as 'tar.gz'


@dataclass
class FieldConf:
    """
    :param pattern: is used for validate input of get_path and get_parent_path, and also for getting fields using
                    parse_path
    :param date_format: date_format and datetime_format are using for a second validation using parse_path,
      for defining the how to cast the string (date or datetime, depending on the argument that was use)
      and for get_path and get_parent_path of accepting either a string or a datetime object that can be
      formated to input for a template string
    :param datetime_format: See description of date_format parameter.
    :param is_optional: allows to omit a field during the path generation (get_path and get_parent_path)
                        or to skip field during the path parsing. IMPORTANT! in order to work properly, pattern must
                        be constrained, otherwise the PathBuilder class may have an unexpected behaviour.
                        For example use '[0-9]{4}' and avoid using '*' or '+' when using is_optional=True
    """

    pattern: str = SafePatterns.FILENAME
    date_format: str | None = None
    datetime_format: str | None = None
    is_optional: bool | None = False
    str_to_var: Callable | None = None
    var_to_str: Callable | None = None

    def __post_init__(self):
        has_date_converter = self.date_format is not None
        has_datetime_converter = self.datetime_format is not None
        has_custom_converter = self.var_to_str is not None or self.str_to_var is not None
        active_converters_num = sum([has_date_converter, has_datetime_converter, has_custom_converter])
        if active_converters_num > 1:
            raise ValueError(f"Maximum one field converter is allowed, but {active_converters_num} were found")

    def replace(self, **kwargs) -> Self:
        """
        Creates a copy of the current object replacing attributes with the given keyword arguments

        :param kwargs: Attributes to be replaced
        :return: An FieldConf object with the attributes replaced
        """
        field_conf = replace(self, **kwargs)
        return field_conf


class PathBuilder:
    """
    Path Builder allows to define, create and parse templated paths

    It defines a path via a path template and its fields. Once instantiated, it allows to create new paths
    and to parse path strings to recover individual fields.

    """

    template: str
    fields: dict[str, FieldConf]
    default_field: FieldConf
    parent_template: str
    _dir_sep: str = "/"

    def __init__(
        self,
        template: str,
        parent_template: str | None = None,
        fields: dict[str, FieldConf] | None = None,
        default_field: FieldConf | None = None,
    ):
        self.template = template

        if parent_template is None:
            parent_template = os.path.dirname(self.template)
        self.check_parent_path_template(template, parent_template)
        self.parent_template = parent_template

        if default_field is None:
            default_field = FieldConf()
        self.default_field = default_field

        new_fields = {}
        template_field_names = self.get_template_fields_names(template)
        for field_name in template_field_names:
            new_fields[field_name] = default_field

        if fields is not None:
            new_fields.update(fields)
        self.fields = new_fields

        self.check_template_fields(template, new_fields)

    def __repr__(self):
        return f"<Template: '{self.template}', Fields: {self.fields}>"

    def replace(self, **kwargs) -> Self:
        """
        Creates a copy of the current object replacing attributes with the given keyword arguments

        :param kwargs: Attributes to be replaced, same arguments as used for PathBuilder instantiation
        :return: A PathBuilder instance
        """
        default_parent_template = None
        if "template" not in kwargs:
            kwargs["template"] = self.template
            default_parent_template = self.parent_template
        if "parent_template" not in kwargs:
            kwargs["parent_template"] = default_parent_template
        if "fields" not in kwargs:
            kwargs["fields"] = self.fields
        if "default_field" not in kwargs:
            kwargs["default_field"] = self.default_field

        return self.__class__(**kwargs)

    def update(self, **kwargs) -> Self:
        """
        Creates a copy of the current object updating attributes with the given keyword arguments
        :param kwargs: Attributes to be updated, same arguments as used for PathBuilder instantiation.
                       Fields set to None, will be reset to default, if it is no longer present on the template, it will
                       be removed.
        :return: A PathBuilder instance
        """
        fields = self.fields.copy()
        if "fields" in kwargs:
            fields.update(kwargs["fields"])
            fields_names = list(fields.keys())
            [fields.pop(n) for n in fields_names if fields[n] is None]  # remove fields set to None from input args
            kwargs["fields"] = fields
        return self.replace(**kwargs)

    def __call__(self, **kwargs) -> Self:
        if not kwargs:
            return self
        return self.replace(**kwargs)

    @staticmethod
    def get_template_fields_names(path_template: str) -> list[str]:
        """
        Get fields names from path template string

        :param path_template: String. Path template that follows string.Formatter() syntax.
        :return: List. Template fields names.
        """
        parsed_field_tuples = list(string.Formatter().parse(path_template))
        template_fields_names = [name for (text, name, spec, conv) in parsed_field_tuples if name is not None]
        return template_fields_names

    @classmethod
    def check_template_fields(cls, path_template: str, map_dict: dict[str:Any]) -> None:
        """
        Check if fields in the path_template are coherent with keys in the given map_dict

        :param path_template: String. Path template that follows string.Formatter() syntax.
        :param map_dict: A dictionary where each key represent a field of the template and each value is string to be
                         mapped
        """
        template_fields = cls.get_template_fields_names(path_template)
        invalid_fields = [f for f in map_dict if f not in template_fields]
        if invalid_fields:
            raise ValueError(f"Invalid fields: {invalid_fields} they do not exist on path_template: '{path_template}'")

        missing_fields = [f for f in template_fields if f not in map_dict]
        if missing_fields:
            raise ValueError(f"Missing fields: {missing_fields} they are required in path_template: '{path_template}'")

    @staticmethod
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

    @classmethod
    def parse_fields(
        cls,
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
        cls.check_template_fields(template, pattern_dict)
        template_fields = cls.get_template_fields_names(template)

        # Deduplicate repeated fields of pattern_dict:
        # for example the template "/{base_path}/{asset_name}/{asset_name}_{suffix}"
        # will become "/{base_path}/{asset_name__0}/{asset_name__1}_{suffix}"
        # and the dict {"base_path": r"\w+", "asset_name": r"\w+", "suffix": r"\d+"}
        # will become {"base_path": r"\w+", "asset_name__0": r"\w+", "asset_name__1": r"\w+", "suffix": r"\d+"}
        unique_fields = list(set(template_fields))
        deduplicated_fields_dict = {}
        new_pattern_dict = {}
        new_template = template
        for field_name in unique_fields:
            field_count = len([f for f in template_fields if f == field_name])
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
        named_pattern_dict = cls.assign_groupname_pattern_dict(pattern_dict)
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

    def parse_file_path(self, file_path: str, raise_error: bool = False) -> dict[str:Any]:
        """
        Parse a file path

        :param file_path: String to be parsed.
        :param raise_error: Whether to raise an exception if the file path is not valid. By default, it returns None.
        :return: Dictionary where each key represent a field of the template and each value is the corresponding parsed
                 string (or converted object)
        """
        ds = self._dir_sep
        path_template = self.template
        path_template = path_template.replace(r".", r"\.")
        pattern_dict = {}
        for field_name, field_conf in self.fields.items():
            field_pattern = field_conf.pattern
            if field_conf.is_optional:
                field_pattern = f"{field_pattern}|"
                # Allow optional directory separator for this field: "/" -> "/?", by updating path_template
                field_name_dir_sep = "{" + field_name + "}" + ds + "{"
                optional_field_name_dir_sep = "{" + field_name + "}" + ds + "?{"
                path_template = path_template.replace(field_name_dir_sep, optional_field_name_dir_sep)
            pattern_dict[field_name] = field_pattern
        parsed_fields = self.parse_fields(file_path, path_template, pattern_dict, raise_error=raise_error)
        processed_fields = self.process_parsed_fields_values(parsed_fields)
        return processed_fields

    @classmethod
    def check_parent_path_template(cls, path_template: str, parent_path_template: str) -> None:
        """
        Check if parent_path_template is coherent with path_template

        :param path_template: String. Path template that follows string.Formatter() syntax.
        :param parent_path_template: String. Parent path template that follows string.Formatter() syntax.
        """
        if parent_path_template not in path_template:
            raise ValueError(
                f"path_template: '{path_template}' does not match with parent_path_template: "
                f"'{parent_path_template}'. parent_path_template must be a substring of path_template"
            )

    @classmethod
    def prepare_fields_values(
        cls, fields_values_dict: dict[str:Any], fields_conf: dict[str, FieldConf]
    ) -> dict[str:str]:
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

    def process_parsed_fields_values(self, parsed_fields: dict[str:str]) -> dict[str:Any]:
        """
        Process fields values dictionary obtained from parsing a file path
        :param parsed_fields: A dictionary of parsed fields values in string format.
        :return: A processed dictionary of fields with converted values depending on each FieldConf definition.
        """
        new_parsed_fields = parsed_fields.copy()

        for field_name, field_value in new_parsed_fields.items():
            if field_name not in self.fields:
                raise ValueError(f"Unknown field '{field_name}'. Valid fields are: {self.fields.keys()}")
            field_conf = self.fields[field_name]

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

    @classmethod
    def _get_path(
        cls,
        template: str,
        fields_conf: dict[str, FieldConf],
        fields_values_dict: dict[str, Any],
    ) -> str:
        """
        Generate path using input parameters

        :param template: A template that follows string.Formatter() syntax.
        :param fields_conf: Dictionary of fields configurations, where keys are field names and values are FieldConf
                            instances.
        :param fields_values_dict: Input parameters dict that maps template fields to values.
        :return: String. Path.
        """
        fields_values_dict = fields_values_dict.copy()
        template_fields = cls.get_template_fields_names(template)
        missing_fields = [field for field in template_fields if field not in fields_values_dict]

        for field_name in missing_fields:
            is_optional = fields_conf[field_name].is_optional
            if is_optional:
                fields_values_dict[field_name] = None

        cls.check_template_fields(template, fields_values_dict)
        fields_values_dict = cls.prepare_fields_values(fields_values_dict, fields_conf)
        new_path = template.format(**fields_values_dict)
        new_path = os.path.normpath(new_path)
        return new_path

    def get_path(self, **kwargs) -> str:
        """
        Generate path using input parameters

        :param kwargs: Input parameters that maps template fields to values.
        :return: String. Path.
        """
        return self._get_path(template=self.template, fields_conf=self.fields, fields_values_dict=kwargs)

    def get_parent_path(self, **kwargs) -> str:
        """
        Generate parent path using input parameters

        :param kwargs: Input parameters that maps template fields to values. They are used in the order of
                       parent_template, if the last argument(s) are omitted, the parent_template will be dynamically
                       updated to a shorter version. If an argument in the middle is omitted, and it is not optional,
                       an error will be raised.
        :return: String. Parent path.
        """

        # remove all fields not present in parent template
        parent_fields = self.fields.copy()
        fields_names = self.get_template_fields_names(self.template)
        parent_fields_names = self.get_template_fields_names(self.parent_template)

        # Drop fields corresponding to filename
        for field in fields_names:
            if field not in parent_fields_names:
                parent_fields.pop(field)

        # Make dynamic the parent path creation, so the last fields can be omitted
        # for example "{a}/{b}/{c}/{d}/" or "{a}/{b}/{c}/" or "{a}/{b}/"
        new_parent_template = self.parent_template
        dynamic_fields_names = []
        missing_kwarg_name = None
        for parent_field_name in parent_fields_names:
            is_optional = parent_fields[parent_field_name].is_optional
            if parent_field_name not in kwargs and not is_optional:
                # keep known (left) part of parent_template and drop the rest
                missing_kwarg_name = parent_field_name
                new_parent_template = new_parent_template.split("{" + parent_field_name + "}", 1)[0]
                break
            dynamic_fields_names.append(parent_field_name)

        # Drop fields corresponding to last arguments that were skipped
        parent_fields_names = list(parent_fields.keys())
        for field_name in parent_fields_names:
            if field_name not in dynamic_fields_names:
                parent_fields.pop(field_name)

        # Check for unnecessary extra args
        extra_kwargs = {}
        for field_name in kwargs:
            if field_name not in parent_fields:
                extra_kwargs[field_name] = kwargs[field_name]
        if missing_kwarg_name and extra_kwargs:
            raise ValueError(
                f"Unexpected extra kwargs: {extra_kwargs}, after updating parent template "
                f"to '{new_parent_template}' because of missing kwarg: '{missing_kwarg_name}'"
            )

        return self._get_path(
            template=new_parent_template,
            fields_conf=parent_fields,
            fields_values_dict=kwargs,
        )

    def assert_path_bijection(self, test_path: str):
        """
        Assert path bijection

        It tries to recover the same initial input after processing once with parse_file_path and get_path

        :param test_path: Path string to be tested
        """
        parsed_fields = self.parse_file_path(test_path, raise_error=True)
        result_test_path = self.get_path(**parsed_fields)
        assert test_path == result_test_path, f"{test_path} != {result_test_path}"

    def assert_fields_bijection(self, test_fields: dict[str, Any]):
        """
        Assert fields bijection

        It tries to recover the same initial input after processing once with get_path and parse_file_path
        This method is the preferred way of checking if the PathBuilder was well-defined.

        :param test_fields: Dictionary of fields to be tested
        """
        test_path = self.get_path(**test_fields)
        result_parsed_fields = self.parse_file_path(test_path, raise_error=True)
        assert test_fields == result_parsed_fields, f"{test_fields} != {result_parsed_fields}"
