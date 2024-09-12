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

# col_names = WellDataColumnNames(
#     well_id="API Well Number",
#     latitude="Latitude",
#     longitude="Longitude",
#     operator_name="Operator Name",
#     age="Age [Years]",
#     depth="Depth [ft]",
#     leak="Leak [Yes/No]",
#     compliance="Compliance [Yes/No]",
#     violation="Violation [Yes/No]",
#     incident="Incident [Yes/No]",
#     hospitals="Number of Nearby Hospitals",
#     schools="Number of Nearby Schools",
#     ann_gas_production="Gas [Mcf/Year]",
#     ann_oil_production="Oil [bbl/Year]",
#     # These are user-specific columns
#     additional_columns={
#         "elevation_delta": "Elevation Delta [m]",
#         "dist_to_road": "Distance to Road [miles]",
#     },
# )
# # wd = WellData(filename="../demo/cluster_Cluster 2.csv", column_names=col_names)
# wd = pd.read_csv("../demo/cluster_Cluster 2.csv")


class DescriptionType(Enum):
    AGE = 1
    DEPTH = 2
    ELEVATION = 3
    OIL_PRODUCTION = 4
    GAS_PRODUCTION = 5
    IMPACT_SCORE = 6
    # for now leaving out our computed scores, except for impact
    # AGE_SCORE = 7
    # WELL_COUNT_SCORE = 8
    # LEAK_SCORE = 9
    # COMPLIANCE_SCORE = 10
    # VIOLATION_SCORE = 11
    # INCIDENT_SCORE = 12
    # HOSPITAL_SCORE = 13
    # SCHOOL_SCORE = 14
    ACCESS = 15
    LEAK = 16
    VIOLATION = 17
    INCIDENT = 18
    COMPLIANCE = 19
    HOSPITAL = 20
    SCHOOL = 21
    OWNER = 22


class WarningType(Enum):
    AGE = 1


class ProjectDescriptor(object):
    """
    Class for describing projects
    """

    def __init__(self, well_data: pd.DataFrame, project_id: int):
        """
        Constructs the project descriptor object for describing projects
        Parameters
        ----------
        well_data : pd.DataFrame
            The data from a WellData object associated with a particular project

        project_id_col_name : str
            The name of the column that labels which project the well is assigned to
        """
        self.well_data = well_data
        self.project_id = project_id
        self.project_info = ProjectInfo(project_id)
        self._populate_project_info_stats_statements()
        self._populate_project_info_count_statements()

    # def _count_statement(self, descriptor_str : str, num_wells : int):
    #     """
    #     Creates a message that uses well counts
    #     """
    #     return f"There are {num_wells} " + descriptor_str

    # def _get_count_statement_from_bool_col(self, descriptor_str : str, col_name : str) -> str:
    #     """
    #     Creates the count statement from a boolean column
    #     """
    #     return self._count_statement(descriptor_str, self._get_count_data_bool_col(col_name))

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

    # def _get_count_statement_from_int_col(self, descriptor_str : str, col_name : str) -> str:
    #     """
    #     Creates the count statement from a column of integers
    #     """
    #     # assume that there are not wells with different data
    #     assert self.well_data[col_name].value_counts()[self.well_data[col_name].values[0]] == len(self.well_data[col_name])
    #     return self._count_statement(descriptor_str, self.well_data[col_name].values[0])

    def _populate_project_info_count_statements(self):
        """
        Adds count descriptions to the project info object
        """
        important_statements = {
            DescriptionType.LEAK: ["Leak [Yes/No]", "Number of wells with leaks", True],
            DescriptionType.VIOLATION: [
                "Violation [Yes/No]",
                "Number of wells with violations",
                True,
            ],
            DescriptionType.INCIDENT: [
                "Incident [Yes/No]",
                "Number of wells with incidents",
                True,
            ],
            DescriptionType.COMPLIANCE: [
                "Compliance [Yes/No]",
                "Number of wells with compliance",
                True,
            ],
            DescriptionType.HOSPITAL: [
                "Number of Nearby Hospitals",
                "Number of hospitals nearby",
                False,
            ],
            DescriptionType.SCHOOL: [
                "Number of Nearby Schools",
                "Number of schools nearby",
                False,
            ],
        }
        for descr_type, labels in important_statements.items():
            col_name, descriptor_str, is_bool_col = labels
            if is_bool_col:
                # self.project_info.add_description(descr_type,
                #     self._get_count_statement_from_bool_col(descriptor_str, col_name))
                self.project_info.add_row_data(
                    descriptor_str,
                    "-",
                    "-",
                    "-",
                    self._get_count_data_bool_col(col_name),
                )
            else:
                # self.project_info.add_description(descr_type,
                #     self._get_count_statement_from_int_col(descriptor_str, col_name)
                # )
                self.project_info.add_row_data(
                    descriptor_str,
                    "-",
                    "-",
                    "-",
                    self._get_count_data_int_col(col_name),
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

    # def _stats_statement(self, descriptor_str : str, average : float,
    #     max_val : Union[int, float], min_val : Union[int, float]) -> str:
    #     """
    #     Creates a message that uses average, min, and max of well data
    #     """
    #     return f"The wells in Project {self.project_id} have an average " + descriptor_str + \
    #             f" of {average}, with a maximum " + descriptor_str + f" of {max_val} and a minimium " + \
    #             descriptor_str + f" of {min_val}."

    # def _get_stats_description_from_column(self, col_name : str, descriptor_str : str) -> str:
    #     """
    #     Returns a statement of stats for a particular column from a pd.DataFrame
    #     """
    #     return self._stats_statement(descriptor_str, *self._get_stats_data_from_column(col_name))

    def _populate_project_info_stats_statements(self):
        """
        Adds all stats descriptions to the project info object
        """
        important_statements = {
            DescriptionType.AGE: ["Age [Years]", "Age (yrs)"],
            DescriptionType.DEPTH: ["Depth [ft]", "Depth (ft)"],
            DescriptionType.ELEVATION: [
                "Elevation Delta [m]",
                "Difference in Elevation (m)",
            ],
            DescriptionType.OIL_PRODUCTION: [
                "Oil [bbl/Year]",
                "Oil Production (bbl/yr)",
            ],
            DescriptionType.GAS_PRODUCTION: [
                "Gas [Mcf/Year]",
                "Gas Production (MCF/yr)",
            ],
            DescriptionType.ACCESS: [
                "Distance to Road [miles]",
                "Distance to Road (miles)",
            ],
            DescriptionType.IMPACT_SCORE: [
                "Priority Score [0-100]",
                "Impact Score (0-100)",
            ],
            DescriptionType.OWNER: [
                "Owner Well-Count",
                "Number of wells owned by owners",
            ],
        }
        for descr_type, labels in important_statements.items():
            # self.project_info.add_description(descr_type, self._get_stats_description_from_column(*labels))
            self.project_info.add_row_data(
                labels[1], *self._get_stats_data_from_column(labels[0]), "-"
            )

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

    def _add_info(self, info_type: DescriptionType, message: str, info_container: dict):
        """
        Adds information to an information container
        """
        # each enum corresponds to a different type of warning or description
        # we only allow one message
        if info_type in info_container:
            raise ValueError("The project already has info of this type")
        info_container[info_type] = message

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

    def add_warning(self, info_type: DescriptionType, message: str):
        """
        Adds a warning to the project info

        Parameters
        ----------
        info_type : DescriptionType
            The type of info

        message : str
            The information
        """
        self._add_info(info_type, message, self.warnings)

    def add_description(self, info_type: DescriptionType, message: str):
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
        print(
            tabulate(
                self.description_data,
                headers=self.header_vals,
                tablefmt="rounded_grid",
                numalign="right",
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
        # self._print_descriptions()
        self._print_project_summary()
        self._print_project_warnings()


# if __name__ == "__main__":
#     project_id = 2
#     test = ProjectDescriptor(wd, project_id)

#     # tests for these functions
#     test._populate_project_info_stats_statements()
#     test._populate_project_info_count_statements()
#     test.print_project_info()
