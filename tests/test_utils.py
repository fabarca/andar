import unittest

from andar.check_utils import check_expected_fields, check_parent_path_template
from andar.parser_utils import assign_groupname_pattern_dict, get_template_fields_names, parse_fields


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

    def test_parse_filename_fields(self):
        filename_template = "{id}_{name}_{date}.{extension}"
        pattern_dict = {
            "id": "[0-9]{5}",
            "name": "[a-zA-Z_]+",
            "date": r"[0-9]{8}",
            "extension": "txt",
        }
        filename = "12345_custom_name_20240101.txt"
        fields_dict = parse_fields(filename, filename_template, pattern_dict, raise_error=True)
        expected_fields_dict = {
            "id": "12345",
            "name": "custom_name",
            "date": "20240101",
            "extension": "txt",
        }
        self.assertEqual(expected_fields_dict, fields_dict)

        wrong_filename = "12345_custom_name_2024-01-01.txt"
        with self.assertRaises(ValueError) as cm:
            parse_fields(wrong_filename, filename_template, pattern_dict, raise_error=True)
        expected_error_msg = f"Invalid string '{wrong_filename}', expected pattern"
        self.assertIn(expected_error_msg, str(cm.exception))

        # test repeated fields
        filename_template = "{folder}/{version}/{name}_{version}.{extension}"
        pattern_dict = {
            "folder": "[a-zA-Z_]+",
            "version": "v[0-9]+",
            "name": "[a-zA-Z_]+",
            "extension": "txt",
        }
        filename = "somewhere/v2/custom_name_v2.txt"
        fields_dict = parse_fields(filename, filename_template, pattern_dict, raise_error=True)
        expected_fields_dict = {
            "folder": "somewhere",
            "name": "custom_name",
            "version": "v2",
            "extension": "txt",
        }
        self.assertEqual(expected_fields_dict, fields_dict)

        filename = "somewhere/v2/custom_name_v3.txt"
        with self.assertRaises(ValueError) as cm:
            parse_fields(filename, filename_template, pattern_dict, raise_error=True)
        expected_error_msg = "More than one value was found for repeated field 'version': ['v2', 'v3']"
        self.assertIn(expected_error_msg, str(cm.exception))

    def test_assign_groupname_pattern_dict(self):
        test_pattern_dict = {"field_a": r"\w+", "field_b": r"\d{4}"}
        groupname_pattern_dict = assign_groupname_pattern_dict(test_pattern_dict)
        expected_groupname_pattern_dict = {
            "field_a": r"(?P<field_a>\w+)",
            "field_b": r"(?P<field_b>\d{4})",
        }
        self.assertEqual(expected_groupname_pattern_dict, groupname_pattern_dict)
