import os.path
import re
from typing import Any, Self

from andar.check_utils import check_expected_fields, check_parent_path_template
from andar.field_conf import FieldConf
from andar.parser_utils import (
    compile_path_regex,
    fusion_deduplicated_fields,
    get_template_fields_names,
    prepare_fields_values,
    process_parsed_fields_values,
)


class PathModel:
    """
    PathModel allows to define, build and parse templated file paths

    It defines a path via a template and its fields. Once instantiated, it allows to build new paths
    and to parse path strings to recover individual fields.

    Attributes:
        template: A template string
        fields: A dictionary of FieldConfs
    """

    template: str
    fields: dict[str, FieldConf]
    default_field: FieldConf
    parent_template: str
    description: str
    compiled_regex: re.Pattern
    _dir_sep: str = "/"

    def __init__(
        self,
        template: str,
        *,
        fields: dict[str, FieldConf] | None = None,
        default_field: FieldConf | None = None,
        parent_template: str | None = None,
        description: str | None = None,
    ):
        self.template = template
        self._fields = fields
        self._parent_template = parent_template
        self._default_field = default_field
        self._description = description

        if parent_template is None:
            parent_template = os.path.dirname(self.template)
        check_parent_path_template(template, parent_template)
        self.parent_template = parent_template

        if default_field is None:
            default_field = FieldConf()
        self.default_field = default_field

        new_fields = {}
        template_field_names = get_template_fields_names(template)
        for field_name in template_field_names:
            new_fields[field_name] = default_field

        if fields is not None:
            new_fields.update(fields)
        self.fields = new_fields

        new_field_names = list(new_fields.keys())
        check_expected_fields(template_field_names, new_field_names)

        if description is None:
            description = ""
        self.description = description

        self.compiled_regex = compile_path_regex(
            template=self.template,
            fields=self.fields,
            ds=self._dir_sep,
        )

    def __repr__(self):
        ident = "  "
        formatted_fields = "\n".join([f"{ident * 2}'{k}': {v}," for k, v in self.fields.items()])
        formatted_args = [f"{ident}template='{self.template}',"]
        if self._fields is not None:
            formatted_args.append(f"{ident}fields={{\n{formatted_fields}\n  }},")
        if self._default_field is not None:
            formatted_args.append(f"{ident}default_field={self.default_field},")
        if self._parent_template is not None:
            formatted_args.append(f"{ident}parent_template='{self.parent_template}',")
        if self._description is not None:
            formatted_args.append(f"{ident}description='{self.description}',")
        formatted_args_str = "\n".join(formatted_args)
        repr = f"PathModel(\n{formatted_args_str}\n)"
        return repr

    def replace(self, copy_description: bool = False, **kwargs: Any) -> Self:
        """
        Creates a copy of the current object replacing attributes with the given keyword arguments

        Params:
            **kwargs: Attributes to be replaced, same arguments as used for PathModel instantiation

        Returns:
            A PathModel instance
        """
        default_parent_template = None  # default value when a new template is given, if not it reuse a previous one
        if "template" not in kwargs:
            kwargs["template"] = self.template
            default_parent_template = self._parent_template
        if "parent_template" not in kwargs:
            kwargs["parent_template"] = default_parent_template  # reset to None when a new template is set
        if "fields" not in kwargs:
            kwargs["fields"] = self._fields
        if "default_field" not in kwargs:
            kwargs["default_field"] = self._default_field
        default_description = None
        if copy_description:
            default_description = self._description
        if "description" not in kwargs:
            kwargs["description"] = default_description

        return self.__class__(**kwargs)

    def update(self, **kwargs: Any) -> Self:
        """
        Creates a copy of the current object updating attributes with the given keyword arguments

        Params:
            **kwargs: Attributes to be updated, same arguments as used for PathModel instantiation.
                      Fields set to `None` will be reset to default_field, if no longer present in the template,
                      they will be removed instead.

        Returns:
            A PathModel instance
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

    def parse_path(self, file_path: str, raise_error: bool = False) -> dict[str:Any]:
        """
        Parse a file path

        Params:
            file_path: String to be parsed.
            raise_error: Whether to raise an exception if the file path is not valid. By default, it returns None.

        Returns:
            Dictionary where each key represent a field of the template and each value is the corresponding parsed
            string (or converted object)
        """

        match = self.compiled_regex.match(file_path)
        if not match:
            if raise_error:
                raise ValueError(f"Invalid path '{file_path}', expected pattern: '{self.compiled_regex.pattern}'")
            return None
        parsed_fields_dict = match.groupdict()
        parsed_fields_dict = fusion_deduplicated_fields(parsed_fields_dict)

        processed_fields = process_parsed_fields_values(self.fields, parsed_fields_dict)
        return processed_fields

    @classmethod
    def _get_path(
        cls,
        template: str,
        fields_conf: dict[str, FieldConf],
        fields_values_dict: dict[str, Any],
    ) -> str:
        """
        Generate path using input parameters

        Params:
            template: A template that follows string.Formatter() syntax.
            fields_conf: Dictionary of fields configurations, where keys are field names and values are FieldConf
                         instances.
            fields_values_dict: Input parameters dict that maps template fields to values.

        Returns:
            A path string.
        """
        fields_values_dict = fields_values_dict.copy()
        template_field_names = get_template_fields_names(template)
        missing_field_names = [field for field in template_field_names if field not in fields_values_dict]

        for field_name in missing_field_names:
            is_optional = fields_conf[field_name].is_optional
            if is_optional:
                fields_values_dict[field_name] = None

        given_field_names = list(fields_values_dict.keys())
        check_expected_fields(template_field_names, given_field_names)
        fields_values_dict = prepare_fields_values(fields_values_dict, fields_conf)
        built_path = template.format(**fields_values_dict)

        # Clean path of duplicated slashes using normpath() when optional fields are present
        normalized_path = os.path.normpath(built_path)
        if built_path.startswith("./"):
            # for preserving bijection of first field when field value is a dot `"."`
            normalized_path = "./" + normalized_path

        return normalized_path

    def get_path(self, **kwargs: Any) -> str:
        """
        Generate path using input parameters

        Params:
            **kwargs: Input parameters that maps template fields to values.

        Returns:
            A path string.
        """
        return self._get_path(template=self.template, fields_conf=self.fields, fields_values_dict=kwargs)

    def get_parent_path(self, **kwargs: Any) -> str:
        """
        Generate parent path using input parameters

        Params:
            **kwargs: Input parameters that maps template fields to values. They are used in the order of
                      parent_template, if the last argument(s) are omitted, the parent_template will be dynamically
                      updated to a shorter version. If an argument in the middle is omitted, and it is not optional,
                      an error will be raised.

        Returns:
            Parent path string.
        """

        # remove all fields not present in parent template
        parent_fields = self.fields.copy()
        fields_names = get_template_fields_names(self.template)
        parent_fields_names = get_template_fields_names(self.parent_template)

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

        Params:
            test_path: Path string to be tested
        """
        parsed_fields = self.parse_path(test_path, raise_error=True)
        result_test_path = self.get_path(**parsed_fields)
        assert test_path == result_test_path, f"{test_path} != {result_test_path}"

    def assert_fields_bijection(self, test_fields: dict[str, Any]):
        """
        Assert fields bijection

        It tries to recover the same initial input after processing once with get_path and parse_file_path
        This method is the preferred way of checking if the PathModel was well-defined.

        Params:
            test_fields: Dictionary of fields to be tested
        """
        test_path = self.get_path(**test_fields)
        result_parsed_fields = self.parse_path(test_path, raise_error=True)
        assert test_fields == result_parsed_fields, f"{test_fields} != {result_parsed_fields}"
