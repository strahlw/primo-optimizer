# Construct an object to store column names
# Standard libs
import sys
from enum import Enum
from typing import Union

# Installed libs
import pandas as pd
from tabulate import tabulate

# User-defined libs
from primo.data_parser import ImpactMetrics, WellData, WellDataColumnNames


class ProjectDescriptor(object):
    """
    Class for describing projects
    """

    def __init__(
        self,
        well_data: pd.DataFrame,
        project_id: int,
        well_cols: WellDataColumnNames,
        num_wells: int,
    ):
        """
        Constructs the project descriptor object for describing projects
        Parameters
        ----------
        well_data : pd.DataFrame
            The data from a WellData object associated with a particular project

        project_id: str
            The label of the project

        well_cols : WellDataColumnNames
            A WellDataColumnNames object associated with well_data

        num_wells: int
            Number of wells in the project
        """
        self.filler_char = "-"
        self.well_data = well_data
        self.project_id = project_id
        self.project_info = ProjectInfo(project_id)
        self.project_info.add_row_data("Number of wells ", "-", "-", "-", num_wells)
        self.well_cols = well_cols
        self._populate_project_info_all_statements()

    def _get_count_data_bool_col(self, col_name: str):
        """
        Gets the count data from a boolean column
        """
        return self.well_data[col_name].sum()

    def _get_count_data_int_col(self, col_name: str):
        """
        Returns the count data for a column with integers
        """
        # if not self.well_data[col_name].value_counts()[self.well_data[col_name].values[0]] == len(self.well_data[col_name]):
        #     print(self.well_data[col_name].values)
        #     print(len(self.well_data[col_name].values))
        #     sys.exit(0)
        assert self.well_data[col_name].value_counts()[
            self.well_data[col_name].values[0]
        ] == len(self.well_data[col_name])
        return self.well_data[col_name].values[0]

    def _populate_project_info_all_statements(self):
        """
        Populates the summary table in the ProjectInfo class
        """
        for column in self.well_cols.return_column_names_to_summarize_stats():
            self.project_info.add_row_data(
                column, *self._get_stats_data_from_column(column), self.filler_char
            )
        for column in self.well_cols.return_column_names_to_summarize_count():
            self.project_info.add_row_data(
                column,
                self.filler_char,
                self.filler_char,
                self.filler_char,
                self._get_count_data_bool_col(column),
            )

    def _get_stats_data_from_column(self, col_name: str):
        """
        Returns the stats data for a particular column
        """
        return (
            self.well_data[col_name].mean(),
            max(self.well_data[col_name]),
            min(self.well_data[col_name]),
        )

    def _count_warning_statement(self, descriptor_str: str, num_wells: int):
        """
        Creates a warning message
        """
        return f"There are {num_wells} " + descriptor_str

    def print_project_info(self):
        self.project_info.print_project_info()


class ProjectInfo(object):
    """
    Class for storing and querying project info
    """

    def __init__(self, project_id: int):
        """
        Constructs an object with warnings and descriptions for projects
        """
        self.warnings = {}
        self.description = {}
        self.description_data = []
        self.header_vals = ["Well Characteristic", "Average", "Max", "Min", "Count"]
        self.project_id = project_id
        self.info_df = None

    def add_row_data(
        self,
        descriptor_str: str,
        ave_val: Union[str, int, float],
        max_val: Union[str, int, float],
        min_val: Union[str, int, float],
        count: Union[str, int],
    ):
        """
        Adds data to the data field for printing

        Parameters
        ----------
        descriptor_str : str
            Label for the row

        ave_val : Union[str, int, float]
            Value for the average, '-' if a count row

        max_val : Union[str, int, float]
            Value for the maximum, '-' if a count row

        min_val : Union[str, int, float]
            Value for the minimum, '-' if a count row

        count : Union[str, int]
            Value for the count, '-' if a stats row

        """
        self.description_data.append([descriptor_str, ave_val, max_val, min_val, count])

    def add_warning(self, info_type: str, message: str):
        """
        Adds a warning to the project info

        Parameters
        ----------
        info_type : str
            The type of info

        message : str
            The information
        """
        self._add_info(info_type, message, self.warnings)

    def add_description(self, info_type: str, message: str):
        """
        Adds a description to the project info

        Parameters
        ----------
        info_type : DescriptionType
            The type of info

        message : str
            The information
        """
        self._add_info(info_type, message, self.description)

    def _create_datafame(self):
        """
        Creates a dataframe for printing and for output files (csv, excel, etc.)
        """
        self.info_df = pd.DataFrame(self.description_data, columns=self.header_vals)

    def _print_descriptions(self):
        """
        Prints descriptions for the project info class
        """
        for _, message in self.description.items():
            print(message)

    def _print_project_summary(self):
        print("=====================================")
        print(f"========== PROJECT {self.project_id} SUMMARY ========")
        print("=====================================")
        self._create_datafame()
        print(
            tabulate(
                self.info_df,
                headers="keys",
                tablefmt="rounded_grid",
                numalign="right",
                showindex=False,
            )
        )

    def _print_project_warnings(self):
        print("\n")
        print("=====================================")
        print(f"========== PROJECT {self.project_id} WARNINGS =======")
        print("=====================================")

    def print_project_info(self):
        """
        Prints the project information
        """
        self._print_project_summary()
        self._print_project_warnings()
