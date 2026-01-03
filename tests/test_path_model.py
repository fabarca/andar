import datetime as dt
import unittest

from andar import FieldConf, PathModel, SafePatterns


class PathModelTests(unittest.TestCase):
    def test_simple_template(self):
        path_builder = PathModel(template="{base_folder}/{intermediate_folder}/{base_name}_{suffix}.{extension}")
        result_path = path_builder.get_path(
            base_folder="parent_folder",
            intermediate_folder="other_folder",
            base_name="my_data",
            suffix="2000-01-01",
            extension="csv",
        )
        expected_path = "parent_folder/other_folder/my_data_2000-01-01.csv"
        self.assertEqual(expected_path, result_path)

        path_builder.parse_path(expected_path)

        wrong_path = "folder/my_data.csv"
        with self.assertRaises(ValueError) as cm:
            path_builder.parse_path(wrong_path, raise_error=True)
        expected_error_msg = f"Invalid path '{wrong_path}', expected pattern"
        self.assertIn(expected_error_msg, str(cm.exception))

        result_parent_path = path_builder.get_parent_path(
            base_folder="parent_folder",
            intermediate_folder="other_folder",
        )
        expected_parent_path = "parent_folder/other_folder"
        self.assertEqual(expected_parent_path, result_parent_path)

        path_builder = PathModel(
            template="{base_folder}/{intermediate_folder}/{base_name}_{suffix}.{extension}",
            parent_template="{base_folder}",
        )
        result_parent_path = path_builder.get_parent_path(base_folder="parent_folder")
        expected_parent_path = "parent_folder"
        self.assertEqual(expected_parent_path, result_parent_path)

    def test_custom_fields(self):
        new_path_builder = PathModel(
            template="{base_path}/{intermediate_folder}/{base_name}_{suffix}.{extension}",
            fields={
                "base_path": FieldConf(pattern=SafePatterns.DIRPATH),
                "intermediate_folder": FieldConf(pattern=r"\d{4}-\d{2}-\d{2}", date_format="%Y-%m-%d"),
                "base_name": FieldConf(
                    pattern=SafePatterns.NAME,
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

        # test relative base_path `.`:
        test_relative_path = "./2025-02-01/MY_DATA_2025-02-01_123456.csv"
        new_path_builder.assert_path_bijection(test_relative_path)
        input_fields = {
            "base_path": ".",
            "intermediate_folder": custom_date,
            "base_name": "my_data",
            "suffix": custom_datetime,
            "extension": "csv",
        }
        new_path_builder.assert_fields_bijection(input_fields)

    def test_optional_fields(self):
        optional_path_builder = PathModel(
            template="{base_path}/{env}/{intermediate_folder}/{base_name}_{suffix}.{extension}",
            fields={
                "base_path": FieldConf(pattern=SafePatterns.DIRPATH),
                "env": FieldConf(pattern=r"dev|preprod|prod|local", is_optional=True),
                "suffix": FieldConf(pattern=SafePatterns.FIELD, is_optional=True),
            },
        )
        # Test get_path
        test_path = optional_path_builder.get_path(
            env="dev",
            base_path="/parent_folder",
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
        expected_key_error_msg = "Missing fields: ['base_path', 'base_name'] they are required in expected field list"
        self.assertIn(expected_key_error_msg, str(context.exception))

        # Test get_parent_path omitting a field in the parent_path
        test_parent_path = optional_path_builder.get_parent_path(
            # env="dev" is optional and can be omitted
            base_path="/parent_folder",
            intermediate_folder="sub_folder",
        )
        expected_test_parent_path = "/parent_folder/sub_folder"
        self.assertEqual(expected_test_parent_path, test_parent_path)

        # Test get_parent_path omitting a field in the name
        test_path = optional_path_builder.get_path(
            env="dev",
            base_path="/parent_folder",
            intermediate_folder="sub_folder",
            base_name="my_data",
            # suffix="custom_suffix" is optional and can be omitted
            extension="csv",
        )
        expected_test_path = "/parent_folder/dev/sub_folder/my_data_.csv"
        self.assertEqual(expected_test_path, test_path)

        optional_path_builder.assert_path_bijection(expected_test_path)
        input_fields = {
            "base_path": "/parent_folder",
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
        optional_path_builder = PathModel(
            template="{base_path}/{env}/{intermediate_folder}/{base_name}_{suffix}.{extension}",
            fields={
                "env": FieldConf(pattern=r"dev|preprod|prod|local", is_optional=True),
                "base_path": FieldConf(pattern=SafePatterns.DIRPATH),
                "intermediate_folder": FieldConf(pattern=r"\d{4}-\d{2}-\d{2}", date_format="%Y-%m-%d"),
                "base_name": FieldConf(
                    pattern=SafePatterns.NAME,
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
            PathModel(
                template="{folder_a}/{base_name}.{extension}",
                fields={"unknown_field": FieldConf(pattern=SafePatterns.FIELD)},
            )
        expected_error_msg = "Invalid fields: ['unknown_field'] they do not exist in expected field list"
        self.assertIn(expected_error_msg, str(context.exception))

    def test_repeated_fields(self):
        path_builder = PathModel(
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

        fields_dict = path_builder.parse_path(expected_test_path)
        expected_fields = {
            "folder_a": "aaa",
            "base_name": "filename",
            "extension": "txt",
            "version": "v1",
        }
        self.assertEqual(expected_fields, fields_dict)

    def test_path_builder_replace(self):
        path_builder = PathModel(
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
        path_builder = PathModel(
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
        path_builder = PathModel(
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

    def test_dynamic_parent_path_creation(self):
        path_builder = PathModel("/{a}/{b}/{c}/{d}/{name}")
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


if __name__ == "__main__":
    unittest.main()
