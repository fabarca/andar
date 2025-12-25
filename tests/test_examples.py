import datetime as dt
import unittest

from andar.examples import data_mesh_pm, date_archived_pm


class ExamplesTests(unittest.TestCase):
    def test_date_archived_pm(self):
        report_datetime = dt.datetime(year=2025, month=6, day=1, hour=12, minute=15, second=30)
        result_path = date_archived_pm.get_path(
            base_path="company_name/new_project",
            sub_folder="reports",
            date=report_datetime,
            name="clients",
            datetime=report_datetime,
            ext="csv",
        )
        expected_path = "/company_name/new_project/reports/2025-06-01/clients_20250601_121530.csv"
        self.assertEqual(expected_path, result_path)

        date_archived_pm.assert_path_bijection(expected_path)

    def test_data_mesh_pm(self):
        campaing_performane_date = dt.date(year=2025, month=12, day=1)
        result_path = data_mesh_pm.get_path(
            domain="marketing",
            layer="mart",
            product="campaing_performane",
            aggregation="monthly",
            date=campaing_performane_date,
            ext="csv",
        )
        expected_path = "/marketing/mart/campaing_performane/monthly/campaing_performane_20251201.csv"
        self.assertEqual(expected_path, result_path)

        data_mesh_pm.assert_path_bijection(expected_path)
