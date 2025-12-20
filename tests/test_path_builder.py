import datetime as dt
import unittest

from andar import FieldConf, PathBuilder, SafePatterns


class PathBuilderTests(unittest.TestCase):
    def test_simple_template(self):
        path_builder = PathBuilder(template="{base_folder}/{intermediate_folder}/{base_name}_{suffix}.{extension}")
        result_path = path_builder.get_path(
            base_folder="parent_folder",
            intermediate_folder="other_folder",
            base_name="my_data",
            suffix="2000-01-01",
            extension="csv",
        )
        expected_path = "parent_folder/other_folder/my_data_2000-01-01.csv"
        self.assertEqual(expected_path, result_path)

        path_builder.parse_file_path(expected_path)

        result_parent_path = path_builder.get_parent_path(
            base_folder="parent_folder",
            intermediate_folder="other_folder",
        )
        expected_parent_path = "parent_folder/other_folder"
        self.assertEqual(expected_parent_path, result_parent_path)

        path_builder = PathBuilder(
            template="{base_folder}/{intermediate_folder}/{base_name}_{suffix}.{extension}",
            parent_template="{base_folder}",
        )
        result_parent_path = path_builder.get_parent_path(base_folder="parent_folder")
        expected_parent_path = "parent_folder"
        self.assertEqual(expected_parent_path, result_parent_path)

    def test_custom_fields(self):
        new_path_builder = PathBuilder(
            template="{base_path}/{intermediate_folder}/{base_name}_{suffix}.{extension}",
            fields={
                "base_path": FieldConf(pattern=SafePatterns.DIRPATH),
                "intermediate_folder": FieldConf(pattern=r"\d{4}-\d{2}-\d{2}", date_format="%Y-%m-%d"),
                "base_name": FieldConf(
                    pattern=SafePatterns.FILENAME,
                    var_to_str=str.upper,
                    str_to_var=str.lower,
                ),
                "suffix": FieldConf(
                    pattern=r"\d{4}-\d{2}-\d{2}_\d{6}",
                    datetime_format="%Y-%m-%d_%H%M%S",
                ),
                "extension": FieldConf(pattern=r"[a-z]+"),
            },
        )

        custom_datetime = dt.datetime.fromisoformat("2025-02-01 12:34:56")
        custom_date = custom_datetime.date()

        test_path = new_path_builder.get_path(
            base_path="/parent/folder",
            intermediate_folder=custom_date,
            base_name="my_data",
            suffix=custom_datetime,
            extension="csv",
        )

        expected_test_path = "/parent/folder/2025-02-01/MY_DATA_2025-02-01_123456.csv"
        self.assertEqual(expected_test_path, test_path)

        test_parent_path = new_path_builder.get_parent_path(
            base_path="/parent/folder",
            intermediate_folder=custom_date,
        )
        expected_test_parent_path = "/parent/folder/2025-02-01"
        self.assertEqual(expected_test_parent_path, test_parent_path)

        new_path_builder.assert_path_bijection(expected_test_path)
        input_fields = {
            "base_path": "/parent/folder",
            "intermediate_folder": custom_date,
            "base_name": "my_data",
            "suffix": custom_datetime,
            "extension": "csv",
        }
        new_path_builder.assert_fields_bijection(input_fields)

    def test_optional_fields(self):
        optional_path_builder = PathBuilder(
            template="/{base_path}/{env}/{intermediate_folder}/{base_name}_{suffix}.{extension}",
            fields={
                "env": FieldConf(pattern=r"dev|preprod|prod|local", is_optional=True),
                "suffix": FieldConf(pattern=SafePatterns.FIELD, is_optional=True),
            },
        )
        # Test get_path
        test_path = optional_path_builder.get_path(
            env="dev",
            base_path="parent_folder",
            intermediate_folder="sub_folder",
            base_name="my_data",
            suffix="suffix",
            extension="csv",
        )
        expected_test_path = "/parent_folder/dev/sub_folder/my_data_suffix.csv"
        self.assertEqual(expected_test_path, test_path)

        # Test raise error when omitting a mandatory field
        with self.assertRaises(ValueError) as context:
            optional_path_builder.get_path(
                env="dev",
                # base_path is mandatory, and it should not be omitted,
                intermediate_folder="sub_folder",
                # base_name is mandatory, and it should not be omitted,
                # suffix is optional and can be omitted
                extension="csv",
            )
        expected_key_error_msg = "Missing fields: ['base_path', 'base_name'] they are required in path_template"
        self.assertIn(expected_key_error_msg, str(context.exception))

        # Test get_parent_path omitting a field in the parent_path
        test_parent_path = optional_path_builder.get_parent_path(
            # env="dev" is optional and can be omitted
            base_path="parent_folder",
            intermediate_folder="sub_folder",
        )
        expected_test_parent_path = "/parent_folder/sub_folder"
        self.assertEqual(expected_test_parent_path, test_parent_path)

        # Test get_parent_path omitting a field in the name
        test_path = optional_path_builder.get_path(
            env="dev",
            base_path="parent_folder",
            intermediate_folder="sub_folder",
            base_name="my_data",
            # suffix="custom_suffix" is optional and can be omitted
            extension="csv",
        )
        expected_test_path = "/parent_folder/dev/sub_folder/my_data_.csv"
        self.assertEqual(expected_test_path, test_path)

        optional_path_builder.assert_path_bijection(expected_test_path)
        input_fields = {
            "base_path": "parent_folder",
            "env": "dev",
            "intermediate_folder": "sub_folder",
            "base_name": "my_data",
            "suffix": None,
            "extension": "csv",
        }
        optional_path_builder.assert_fields_bijection(input_fields)

    def test_path_builder_converters(self):
        custom_datetime = dt.datetime.fromisoformat("2025-02-01 12:34:56")
        custom_date = custom_datetime.date()
        optional_path_builder = PathBuilder(
            template="{base_path}/{env}/{intermediate_folder}/{base_name}_{suffix}.{extension}",
            fields={
                "env": FieldConf(pattern=r"dev|preprod|prod|local", is_optional=True),
                "base_path": FieldConf(pattern=SafePatterns.DIRPATH),
                "intermediate_folder": FieldConf(pattern=r"\d{4}-\d{2}-\d{2}", date_format="%Y-%m-%d"),
                "base_name": FieldConf(
                    pattern=SafePatterns.FILENAME,
                    var_to_str=str.upper,
                    str_to_var=str.lower,
                ),
                "suffix": FieldConf(
                    pattern=r"\d{4}-\d{2}-\d{2}_\d{6}",
                    datetime_format="%Y-%m-%d_%H%M%S",
                ),
                "extension": FieldConf(pattern=r"[a-z]+"),
            },
        )

        test_path = optional_path_builder.get_path(
            env="dev",
            base_path="/parent/folder",
            intermediate_folder=custom_date,
            base_name="my_data",
            suffix=custom_datetime,
            extension="csv",
        )
        expected_test_path = "/parent/folder/dev/2025-02-01/MY_DATA_2025-02-01_123456.csv"
        self.assertEqual(expected_test_path, test_path)

        test_path = optional_path_builder.get_path(
            # env="dev" is optional and can be omitted
            base_path="/parent/folder",
            intermediate_folder=custom_date,
            base_name="my_data",
            suffix=custom_datetime,
            extension="csv",
        )
        expected_test_path = "/parent/folder/2025-02-01/MY_DATA_2025-02-01_123456.csv"
        self.assertEqual(expected_test_path, test_path)

        test_parent_path = optional_path_builder.get_parent_path(
            env="dev",
            base_path="/parent/folder",
            intermediate_folder=custom_date,
        )
        expected_test_parent_path = "/parent/folder/dev/2025-02-01"
        self.assertEqual(expected_test_parent_path, test_parent_path)

        test_parent_path = optional_path_builder.get_parent_path(
            # env="dev" is optional and can be omitted
            base_path="/parent/folder",
            intermediate_folder=custom_date,
        )
        expected_test_parent_path = "/parent/folder/2025-02-01"
        self.assertEqual(expected_test_parent_path, test_parent_path)

        optional_path_builder.assert_path_bijection(test_path)
        input_fields = {
            "base_path": "/parent/folder",
            "env": None,
            "intermediate_folder": custom_date,
            "base_name": "my_data",
            "suffix": custom_datetime,
            "extension": "csv",
        }
        optional_path_builder.assert_fields_bijection(input_fields)

    def test_unknown_field(self):
        with self.assertRaises(ValueError) as context:
            PathBuilder(
                template="{folder_a}/{base_name}.{extension}",
                fields={"unknown_field": FieldConf(pattern=SafePatterns.FIELD)},
            )
        expected_error_msg = "Invalid fields: ['unknown_field'] they do not exist on path_template"
        self.assertIn(expected_error_msg, str(context.exception))

    def test_repeated_fields(self):
        path_builder = PathBuilder(
            template="{folder_a}/{version}/{base_name}_{version}.{extension}",
        )
        test_path = path_builder.get_path(
            folder_a="aaa",
            base_name="filename",
            version="v1",
            extension="txt",
        )
        expected_test_path = "aaa/v1/filename_v1.txt"
        self.assertEqual(expected_test_path, test_path)

        fields_dict = path_builder.parse_file_path(expected_test_path)
        expected_fields = {
            "folder_a": "aaa",
            "base_name": "filename",
            "extension": "txt",
            "version": "v1",
        }
        self.assertEqual(expected_fields, fields_dict)

    def test_path_builder_replace(self):
        path_builder = PathBuilder(
            template="{folder_a}/{folder_b}/{folder_c}/{base_name}{suffix}.{extension}",
            fields={
                "folder_a": FieldConf(pattern=SafePatterns.FIELD, is_optional=True),
            },
        )

        new_path_builder = path_builder.replace(
            fields={
                "folder_b": FieldConf(pattern=SafePatterns.FIELD, is_optional=True),
            }
        )
        test_parent_path = new_path_builder.get_parent_path(folder_a="aaa", folder_c="ccc")
        expected_test_parent_path = "aaa/ccc"
        self.assertEqual(expected_test_parent_path, test_parent_path)

        new_path_builder = path_builder.replace(
            template="{folder_b}/{folder_a}/{folder_c}/{base_name}{suffix}.{extension}",
        )
        test_path = new_path_builder.get_path(
            folder_a="aaa",
            folder_b="bbb",
            folder_c="ccc",
            base_name="filename",
            suffix="123",
            extension="txt",
        )
        expected_test_path = "bbb/aaa/ccc/filename123.txt"
        self.assertEqual(expected_test_path, test_path)

    def test_path_builder_update(self):
        path_builder = PathBuilder(
            template="{folder_a}/{folder_b}/{folder_c}/{base_name}{suffix}.{extension}",
            fields={
                "folder_b": FieldConf(pattern=SafePatterns.FIELD, is_optional=True),
            },
        )

        new_path_builder = path_builder.update(
            fields={
                "folder_c": FieldConf(pattern=SafePatterns.FIELD, is_optional=True),
            }
        )
        test_parent_path = new_path_builder.get_parent_path(folder_a="aaa")  # now folder_b and folder_c are optional
        expected_test_parent_path = "aaa"
        self.assertEqual(expected_test_parent_path, test_parent_path)

    def test_bijection_errors(self):
        path_builder = PathBuilder(
            template="{a}_{b}_{c}_{d}.{e}",
            fields={
                "c": FieldConf(is_optional=True),
                "d": FieldConf(is_optional=True),
            },
        )
        misleading_path = "a_A_b_B.e"
        path_builder.assert_path_bijection(misleading_path)  # assert_path_bijection does NOT detect this error

        invalid_fields = {"a": "a_A", "b": "b_B", "e": "e"}
        with self.assertRaises(AssertionError) as cm:
            path_builder.assert_fields_bijection(invalid_fields)  # assert_fields_bijection does DETECT the error
        expected_msg = "{'a': 'a_A', 'b': 'b_B', 'e': 'e'} != {'a': 'a', 'b': 'A', 'c': 'b', 'd': 'B__', 'e': 'e'}"
        self.assertIn(expected_msg, str(cm.exception))

    def test_check_parent_path_template(self):
        path_template = "prefix/{a}/{b}"
        parent_path_template = "prefix/{a}"
        PathBuilder.check_parent_path_template(path_template, parent_path_template)

        invalid_parent_path_template = "prefix/{b}"
        with self.assertRaises(ValueError) as cm:
            PathBuilder.check_parent_path_template(path_template, invalid_parent_path_template)
        self.assertIn(
            "parent_path_template must be a substring of path_template",
            str(cm.exception),
        )

    def test_get_template_fields_names(self):
        expected_fields_names = ["a", "b", "c", "a"]
        formated_field_names = ["{" + n + "}" for n in expected_fields_names]
        template_str = "_".join(formated_field_names)
        result_field_names = PathBuilder.get_template_fields_names(template_str)
        self.assertEqual(result_field_names, expected_fields_names)

    def test_check_template_fields(self):
        path_template = "{a}/{b}"
        valid_map_dict = {"a": "aaa", "b": "bbb"}
        PathBuilder.check_template_fields(path_template, valid_map_dict)

        unknown_map_dict = {"c": "unexpected_field"}
        with self.assertRaises(ValueError) as cm:
            PathBuilder.check_template_fields(path_template, unknown_map_dict)
        self.assertIn(
            "Invalid fields: ['c'] they do not exist on path_template",
            str(cm.exception),
        )

        missing_map_dict = {}
        with self.assertRaises(ValueError) as cm:
            PathBuilder.check_template_fields(path_template, missing_map_dict)
        self.assertIn(
            "Missing fields: ['a', 'b'] they are required in path_template",
            str(cm.exception),
        )

    def test_parse_filename_fields(self):
        filename_template = "{id}_{name}_{date}.{extension}"
        pattern_dict = {
            "id": "[0-9]{5}",
            "name": "[a-zA-Z_]+",
            "date": r"[0-9]{8}",
            "extension": "txt",
        }
        filename = "12345_custom_name_20240101.txt"
        fields_dict = PathBuilder.parse_fields(filename, filename_template, pattern_dict, raise_error=True)
        expected_fields_dict = {
            "id": "12345",
            "name": "custom_name",
            "date": "20240101",
            "extension": "txt",
        }
        self.assertEqual(expected_fields_dict, fields_dict)

        wrong_filename = "12345_custom_name_2024-01-01.txt"
        with self.assertRaises(ValueError) as cm:
            PathBuilder.parse_fields(wrong_filename, filename_template, pattern_dict, raise_error=True)
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
        fields_dict = PathBuilder.parse_fields(filename, filename_template, pattern_dict, raise_error=True)
        expected_fields_dict = {
            "folder": "somewhere",
            "name": "custom_name",
            "version": "v2",
            "extension": "txt",
        }
        self.assertEqual(expected_fields_dict, fields_dict)

        filename = "somewhere/v2/custom_name_v3.txt"
        with self.assertRaises(ValueError) as cm:
            PathBuilder.parse_fields(filename, filename_template, pattern_dict, raise_error=True)
        expected_error_msg = "More than one value was found for repeated field 'version': ['v2', 'v3']"
        self.assertIn(expected_error_msg, str(cm.exception))

    def test_dynamic_parent_path_creation(self):
        path_builder = PathBuilder("/{a}/{b}/{c}/{d}/{name}")
        test_parent_path = path_builder.get_parent_path(a="aaa", b="bbb", c="ccc")
        expected_parent_path = "/aaa/bbb/ccc"
        self.assertEqual(expected_parent_path, test_parent_path)

        test_parent_path = path_builder.get_parent_path(a="aaa", b="bbb")
        expected_parent_path = "/aaa/bbb"
        self.assertEqual(expected_parent_path, test_parent_path)

        test_parent_path = path_builder.get_parent_path(a="aaa")
        expected_parent_path = "/aaa"
        self.assertEqual(expected_parent_path, test_parent_path)

        test_parent_path = path_builder.get_parent_path()
        expected_parent_path = "/"
        self.assertEqual(expected_parent_path, test_parent_path)

        with self.assertRaises(ValueError) as context:
            path_builder.get_parent_path(a="aaa", c="ccc")
        expected_key_error_msg = (
            "Unexpected extra kwargs: {'c': 'ccc'}, after updating parent template to '/{a}/' "
            "because of missing kwarg: 'b'"
        )
        self.assertIn(expected_key_error_msg, str(context.exception))

    def test_assign_groupname_pattern_dict(self):
        test_pattern_dict = {"field_a": r"\w+", "field_b": r"\d{4}"}
        groupname_pattern_dict = PathBuilder.assign_groupname_pattern_dict(test_pattern_dict)
        expected_groupname_pattern_dict = {
            "field_a": r"(?P<field_a>\w+)",
            "field_b": r"(?P<field_b>\d{4})",
        }
        self.assertEqual(expected_groupname_pattern_dict, groupname_pattern_dict)


if __name__ == "__main__":
    unittest.main()
