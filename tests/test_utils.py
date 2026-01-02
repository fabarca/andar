import unittest

from andar.check_utils import check_expected_fields, check_parent_path_template
from andar.field_conf import FieldConf
from andar.parser_utils import (
    assign_groupname_pattern_dict,
    compile_path_regex,
    fusion_deduplicated_fields,
    get_template_fields_names,
)


class UtilsTests(unittest.TestCase):
    def test_check_expected_fields(self):
        expected_field_names = ["a", "b"]
        new_field_names = ["a", "b"]
        check_expected_fields(expected_field_names, new_field_names)

        unknown_field_names = ["c"]
        with self.assertRaises(ValueError) as cm:
            check_expected_fields(expected_field_names, unknown_field_names)
        self.assertIn(
            "Invalid fields: ['c'] they do not exist in expected field list",
            str(cm.exception),
        )

        missing_field_names = []
        with self.assertRaises(ValueError) as cm:
            check_expected_fields(expected_field_names, missing_field_names)
        self.assertIn(
            "Missing fields: ['a', 'b'] they are required in expected field list",
            str(cm.exception),
        )

    def test_check_parent_path_template(self):
        path_template = "prefix/{a}/{b}"
        parent_path_template = "prefix/{a}"
        check_parent_path_template(path_template, parent_path_template)

        invalid_parent_path_template = "prefix/{b}"
        with self.assertRaises(ValueError) as cm:
            check_parent_path_template(path_template, invalid_parent_path_template)
        self.assertIn(
            "parent_path_template must be a substring of path_template",
            str(cm.exception),
        )

    def test_get_template_fields_names(self):
        expected_fields_names = ["a", "b", "c", "a"]
        formated_field_names = ["{" + n + "}" for n in expected_fields_names]
        template_str = "_".join(formated_field_names)
        result_field_names = get_template_fields_names(template_str)
        self.assertEqual(result_field_names, expected_fields_names)

    def test_fusion_deduplicated_fields(self):
        parsed_field_dict = {
            "name": "data",
            "version__0": "v1",
            "version__1": "v1",
            "version__2": "v1",
            "ext": "csv",
        }
        result_dict = fusion_deduplicated_fields(parsed_field_dict)
        expected_fusioned_dict = {
            "name": "data",
            "version": "v1",
            "ext": "csv",
        }
        self.assertDictEqual(expected_fusioned_dict, result_dict)

        invalid_dict = {
            "name": "data",
            "version__0": "v2",
            "version__1": "v3",
            "ext": "csv",
        }
        with self.assertRaises(ValueError) as cm:
            result_dict = fusion_deduplicated_fields(invalid_dict)
        expected_error_msg = "More than one value was found for repeated field 'version': ['v2', 'v3']"
        self.assertIn(expected_error_msg, str(cm.exception))

    def test_compile_path_regex(self):
        filename_template = "{prefix}_{name}.{extension}"
        fields = {
            "prefix": FieldConf(pattern=r"[0-9]{4}"),
            "name": FieldConf(pattern=r"[a-zA-Z0-9]+"),
            "extension": FieldConf(pattern=r"json"),
        }

        compiled_regex = compile_path_regex(filename_template, fields)
        expected_pattern = r"^(?P<prefix>[0-9]{4})_(?P<name>[a-zA-Z0-9]+)\.(?P<extension>json)$"
        self.assertEqual(expected_pattern, compiled_regex.pattern)

        filename = "0001_example.json"
        parsed_field_dict = compiled_regex.match(filename).groupdict()
        expected_parsed_field_dict = {
            "prefix": "0001",
            "name": "example",
            "extension": "json",
        }
        self.assertDictEqual(expected_parsed_field_dict, parsed_field_dict)

        invalid_template = "{asset__name}.{extension}"
        invalid_fields = {
            "asset__name": FieldConf(pattern=r"[a-zA-Z0-9]+"),
            "extension": FieldConf(pattern=r"json"),
        }

        with self.assertRaises(ValueError) as cm:
            compile_path_regex(invalid_template, invalid_fields)
        expected_error_msg = "Fields cannot contains double underscore: ['asset__name']"
        self.assertIn(expected_error_msg, str(cm.exception))

    def test_assign_groupname_pattern_dict(self):
        test_pattern_dict = {"field_a": r"\w+", "field_b": r"\d{4}"}
        groupname_pattern_dict = assign_groupname_pattern_dict(test_pattern_dict)
        expected_groupname_pattern_dict = {
            "field_a": r"(?P<field_a>\w+)",
            "field_b": r"(?P<field_b>\d{4})",
        }
        self.assertEqual(expected_groupname_pattern_dict, groupname_pattern_dict)
