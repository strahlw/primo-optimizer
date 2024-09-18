#################################################################################
# PRIMO - The P&A Project Optimizer was produced under the Methane Emissions
# Reduction Program (MERP) and National Energy Technology Laboratory's (NETL)
# National Emissions Reduction Initiative (NEMRI).
#
# NOTICE. This Software was developed under funding from the U.S. Government
# and the U.S. Government consequently retains certain rights. As such, the
# U.S. Government has been granted for itself and others acting on its behalf
# a paid-up, nonexclusive, irrevocable, worldwide license in the Software to
# reproduce, distribute copies to the public, prepare derivative works, and
# perform publicly and display publicly, and to permit others to do so.
#################################################################################

# Installed libs
import numpy as np

# User-defined libs
from primo.data_parser import WellData
from primo.utils.geo_utils import get_distance
from primo.utils.kpi_utils import _check_column_name, calculate_average, calculate_range
from primo.utils.project_information_utils import (
    EfficiencyCalculator,
    ProjectDescriptor,
)

INFO_UNAVAILABLE = "INFO_UNAVAILABLE"


class OptimalProject:
    """
    Class for storing optimal projects
    """

    def __init__(
        self, wd: WellData, index: list, plugging_cost: float, project_id: int
    ):
        """
        Constructs an object for storing optimal project results
        Parameters
        ----------
        wd : WellData
            A WellData object

        index : list
            List of indices/rows/wells belonging to the cluster/group

        plugging_cost : float
            Cost of plugging

        project_id : int
            Project id
        """
        # Motivation for storing the entire DataFrame: After the problem is solved
        # it is desired to display/highlight flagged wells for which the information
        # was not available, and the missing data was filled. Having the entire
        # DataFrame allows ease of access to flagged wells (columns containing _flag)
        self.well_data = wd._construct_sub_data(index)
        self._df = wd.data.loc[index]
        self._col_names = self.well_data._col_names
        col_names = self._col_names
        self.project_id = project_id

        # Must display essential columns while printing a DataFrame
        self._essential_cols = [
            col_names.well_id,
            col_names.operator_name,
            col_names.latitude,
            col_names.longitude,
            col_names.age,
            col_names.depth,
        ]
        self._priority_score_cols = wd.get_priority_score_columns
        self._flag_cols = wd.get_flag_columns
        self.num_wells = len(index)
        # Optimization problem uses million USD. Convert it to USD
        self.plugging_cost = plugging_cost * 1e6
        self.project_info = ProjectDescriptor(
            self._df, project_id, self._col_names, self.num_wells
        )
        self._add_distance_to_centroid_col()
        # self.project_efficiency = EfficiencyCalculator(self.well_data)
        print(self.project_id)
        print(self.num_wells_near_hospitals)
        print(self.average_age)
        print(self.num_wells_near_schools)
        print(self.average_depth)
        print(self.age_range)
        print("Elevation average = ", self.elevation_average)
        print("Centroid = ", self.centroid)
        print("Average dist to centroid = ", self.ave_dist_to_centroid)
        print("Average distance to road = ", self.ave_dist_to_road)
        print("Number of well owners = ", self.number_of_well_owners)
        print("Average priority score = ", self.impact_score)
        print("\n")

        # self.project_info.print_project_info()

    def __iter__(self):
        return iter(self._df.index)

    def __str__(self) -> str:
        num_wells = self.num_wells
        num_hospitals = self.num_wells_near_hospitals
        num_schools = self.num_wells_near_schools

        msg = (
            f"Number of wells                 : {num_wells}\n"
            f"Number of wells near hospitals  : {num_hospitals}\n"
            f"Number of wells near schools    : {num_schools}\n"
        )
        return msg

    def _check_column_exists(self, col_name):
        """
        Checks if a column exists
        """
        if col_name is None:
            return INFO_UNAVAILABLE

    @property
    def num_wells_near_hospitals(self):
        """Returns number of wells that are near hospitals"""
        col_name = self._col_names.hospitals
        self._check_column_exists(col_name)

        return len(self.well_data.data[self.well_data.data[col_name] > 0].index)

    @property
    def num_wells_near_schools(self):
        """Returns number of wells that are near schools"""
        col_name = self._col_names.schools
        self._check_column_exists(col_name)
        return len(self.well_data.data[self.well_data.data[col_name] > 0].index)

    @property
    def average_age(self):
        """
        Returns average age of the wells in the project
        """
        col_name = self._col_names.age
        self._check_column_exists(col_name)
        return calculate_average(self.well_data.data, col_name)

    @property
    def age_range(self):
        """
        Returns the range of the age of the project
        """
        col_name = self._col_names.age
        self._check_column_exists(col_name)
        return calculate_range(self.well_data.data, col_name)

    @property
    def average_depth(self):
        """
        Returns the average depth of the project
        """
        col_name = self._col_names.depth
        self._check_column_exists(col_name)
        return calculate_average(self.well_data.data, col_name)

    @property
    def elevation_average(self):
        """
        Returns the average elevation delta of the project
        """
        # TODO ensure this column exists!
        col_name = self._col_names.elevation_delta
        self._check_column_exists(col_name)
        return calculate_average(self.well_data.data, col_name, estimation_method="yes")

    @property
    def centroid(self):
        """
        Returns the centroid of the project
        """
        self._check_column_exists(self._col_names.latitude)
        self._check_column_exists(self._col_names.longitude)
        return tuple(
            np.round(
                np.mean(
                    self.well_data.data[
                        [self._col_names.latitude, self._col_names.longitude]
                    ].values,
                    axis=0,
                ),
                6,
            )
        )

    @property
    def ave_dist_to_centroid(self):
        """
        Returns the average distance to the centroid for a project
        """
        col_name = self._col_names.dist_centroid
        self._check_column_exists(col_name)
        return calculate_average(self.well_data.data, col_name)

    @property
    def ave_dist_to_road(self):
        """
        Returns the average distance to road for a project
        """
        col_name = self._col_names.dist_to_road
        self._check_column_exists(col_name)
        return calculate_average(self.well_data.data, col_name)

    @property
    def number_of_well_owners(self):
        """
        Returns the number of well owners for a project
        """
        col_name = self._col_names.operator_name
        self._check_column_exists(col_name)
        return len(set(self.well_data.data[col_name].values))

    @property
    def impact_score(self):
        """
        Returns the average priority score for the project
        """
        col_name = self._col_names.priority_score
        self._check_column_exists(col_name)
        return calculate_average(self.well_data.data, col_name)

    def _add_distance_to_centroid_col(self):
        """
        Adds the distance to centroid column to the well data
        """
        # I am assuming here that apply returns the data in the corresponding order
        self.well_data.add_new_column_ordered(
            ["dist_centroid", "Distance to Centroid [miles]"],
            self.well_data.data.apply(
                lambda row: get_distance(
                    (row[self._col_names.latitude], row[self._col_names.longitude]),
                    self.centroid,
                ),
                axis=1,
            ).values,
        )

    def return_size_of_col(self, col_name):
        """Returns the size of the column for the project"""
        return len(self._df[col_name])

    def get_max_val_col(self, col_name) -> float:
        """
        Returns the maximum value of a column

        Parameters
        ----------
        col_name : str
            column name

        Returns
        -------
        float
            the maximum value of the column

        """
        _check_column_name(self.well_data.data, col_name)
        return self.well_data.data[col_name].max()


class OptimalCampaign:
    """
    Represents an optimal campaign that consists of multiple projects.
    """

    def __init__(self, wd: WellData, clusters_dict: dict, plugging_cost: dict):
        """
        Represents an optimal campaign that consists of multiple projects.

        Parameters
        ----------
        wd : WellData
            WellData object

        clusters_dict : dict
            A dictionary where keys are cluster numbers and values
            are list of wells for each cluster.

        plugging_cost : dict
            A dictionary where keys are cluster numbers and values
            are plugging cost for that cluster
        """
        # for now include a pointer to well data, so that I have column names
        self.wd = wd

        self._clusters_dict = clusters_dict
        self.projects = {}

        index = 1
        for cluster, wells in clusters_dict.items():
            self.projects[index] = OptimalProject(
                wd=wd,
                index=wells,
                plugging_cost=plugging_cost[cluster],
                project_id=cluster,
            )
            index += 1

        self.num_projects = len(self.projects)
        self.total_cost = sum(plugging_cost.values()) * 1e6

    def __str__(self) -> str:
        msg = (
            f"The optimal campaign has {self.num_projects} projects.\n"
            f"The total cost of the campaing is ${round(self.total_cost)}\n\n"
        )
        for i, obj in self.projects.items():
            msg += f"Project {i} has {obj.num_wells} wells.\n"

        return msg

    def _get_max_num_wells_across_projects(self):
        """
        Return the max values of a column across all projects (for efficiency calculation)
        """
        return max(
            [
                project.return_size_of_col(self.wd.get_col_names().well_id)
                for _, project in self.projects.items()
            ]
        )

    def _get_max_num_owners_across_projects(self):
        """
        Return the max number of owners across all projects (for efficiency calculation)
        """
        return max(
            [
                len(
                    set(
                        project.well_data.data[
                            self.wd.get_col_names().operator_name
                        ].values
                    )
                )
                for _, project in self.projects.items()
            ]
        )
