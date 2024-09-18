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

# Standard libs
import logging
import sys
from typing import Union

# Installed libs
import numpy as np

# User-defined libs
from primo.data_parser import EfficiencyMetrics, WellData
from primo.utils.geo_utils import get_distance
from primo.utils.kpi_utils import _check_column_name, calculate_average, calculate_range
from primo.utils.project_information_utils import ProjectDescriptor

INFO_UNAVAILABLE = "INFO_UNAVAILABLE"
LOGGER = logging.getLogger(__name__)


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
        self.efficiency_score = 0

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
    def depth_range(self):
        """
        Returns the range of the depth of the project
        """
        col_name = self._col_names.depth
        self._check_column_exists(col_name)
        return calculate_range(self.well_data.data, col_name)

    @property
    def ave_elevation_delta(self):
        """
        Returns the average elevation delta of the project
        """
        if not hasattr(self._col_names, "elevation_delta"):
            raise AttributeError("There is no data for the elevation delta")
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
        if not hasattr(self._col_names, "dist_centroid"):
            raise AttributeError("There is no data for the distance to centroid")
        col_name = self._col_names.dist_centroid
        self._check_column_exists(col_name)
        return calculate_average(self.well_data.data, col_name)

    @property
    def ave_dist_to_road(self):
        """
        Returns the average distance to road for a project
        """
        if not hasattr(self._col_names, "ave_dist_to_road"):
            raise AttributeError("There is no data for average distance to road")
        col_name = self._col_names.dist_to_road
        self._check_column_exists(col_name)
        return calculate_average(self.well_data.data, col_name)

    @property
    def num_unique_owners(self):
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

    def update_efficiency_score(self, value: Union[int, float]):
        """
        Updates the efficiency score of a project
        """
        self.efficiency_score += value


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

    def print_project_data(self):
        for _, project in self.projects.items():
            print("Project = ", project.project_id)
            print("Efficiency Score = ", project.efficiency_score)
            print("Average impact score = ", project.impact_score)

    def get_max_value_across_all_projects(self, attribute: str) -> Union[float, int]:
        """
        Returns the max value for an attribute across projects
        """
        if not hasattr(next(iter(self.projects.values())), attribute):
            raise AttributeError(
                "The project does not have the requested attribute: " + attribute
            )
        return max(
            [getattr(project, attribute) for _, project in self.projects.items()]
        )

    def get_min_value_across_all_projects(self, attribute: str) -> Union[float, int]:
        """
        Returns the min value for an attribute across projects
        """
        if not hasattr(next(iter(self.projects.values())), attribute):
            raise AttributeError(
                "The project does not have the requested attribute: " + attribute
            )
        return min(
            [getattr(project, attribute) for _, project in self.projects.items()]
        )

    def _check_col_in_data(self, col_name):
        """
        Checks if the column is in the well data
        """
        if col_name not in self.wd.data.columns:
            raise AttributeError(
                "The well data does not have " + col_name + " as a column name"
            )

    def get_max_value_across_all_wells(self, col_name: str) -> Union[float, int]:
        """
        Returns the max value for all wells in the data set
        """
        self._check_col_in_data(col_name)
        return max(self.wd.data[col_name].values)

    def get_min_value_across_all_wells(self, col_name: str) -> Union[float, int]:
        """
        Returns the max value for all wells in the data set
        """
        self._check_col_in_data(col_name)
        return min(self.wd.data[col_name].values)


class EfficiencyCalculator(object):
    """
    A class to compute efficiency scores for projects.
    """

    def __init__(self, campaign: OptimalCampaign):
        """
        Constructs the object for all of the efficiency computations for a campaign

        Parameters
        ----------

        campaign : OptimalCampaign
            The final campaign for efficiencies to be computed

        """
        self.campaign = campaign
        self.efficiency_weights = None

    def set_efficiency_weights(self, eff_metrics: EfficiencyMetrics):
        """
        Sets the attribute containing the efficiency weights
        """
        self.efficiency_weights = eff_metrics

    def compute_efficiency_attributes_for_all_projects(self):
        """
        Computes efficiency attributes for all the projects in the campaign
        """
        for _, project in self.campaign.projects.items():
            self.compute_efficiency_attributes_for_project(project)

    def compute_efficiency_attributes_for_project(self, project):
        """
        Adds attributes to each project object with the metric efficiency score
        """
        assert self.efficiency_weights is not None
        self.efficiency_weights.check_validity()
        project._col_names.check_columns_available(self.efficiency_weights)

        # for obj in self.efficiency_weights:
        #     print(obj.name)
        # sys.exit(0)
        if project.num_wells == 1:
            # the default efficiency score is 0
            return

        for metric in self.efficiency_weights:
            if metric.weight == 0 or hasattr(metric, "submetrics"):
                # Metric/submetric is not chosen, or
                # This is a parent metric, so no data assessment is required
                continue

            LOGGER.info(
                f"Computing scores for metric/submetric {metric.name}/{metric.full_name}."
            )

            if metric.name == "ave_dist_to_centroid":
                # these are hardcoded...they need to be unchangeable
                max_value = 5
                min_value = 0
            elif metric.name == "num_unique_owners":
                metric.data_col_name = metric.name
                max_value = self.campaign.get_max_value_across_all_projects(metric.name)
                min_value = 1
            elif metric.name == "num_wells":
                metric.data_col_name = metric.name
                max_value = self.campaign.get_max_value_across_all_projects(metric.name)
                min_value = 1
            else:
                max_value = self.campaign.get_max_value_across_all_wells(
                    metric.data_col_name
                )
                min_value = self.campaign.get_min_value_across_all_wells(
                    metric.data_col_name
                )
            assert getattr(project, metric.score_attribute, None) is None
            assert hasattr(project, metric.name)

            # Check if division by a zero is likely
            if np.isclose(max_value, min_value, rtol=0.001):
                # All cells in this column have equal value.
                # To avoid division by zero, set min_value = 0
                min_value = 0

            if np.isclose(max_value, 0, rtol=0.001):
                # All values in this column are likely zeros.
                # To avoid division by zero, set max_value = 1
                max_value = 1.0

            if metric.has_inverse_priority:
                setattr(
                    project,
                    metric.score_attribute,
                    (
                        (max_value - getattr(project, metric.name))
                        / (max_value - min_value)
                    )
                    * metric.effective_weight,
                )

            else:
                setattr(
                    project,
                    metric.score_attribute,
                    (
                        (getattr(project, metric.name) - min_value)
                        / (max_value - min_value)
                    )
                    * metric.effective_weight,
                )

    def compute_overall_efficiency_scores_project(self, project):
        """
        Computes the overall efficiency score for a project
        """
        names_attributes = [i for i in dir(project) if "eff_score" in i]
        assert len(names_attributes) == len(
            [
                metric.name
                for metric in self.efficiency_weights
                if metric.weight != 0 and not hasattr(metric, "submetric")
            ]
        )
        for attr in names_attributes:
            project.update_efficiency_score(getattr(project, attr))

    def compute_overall_efficiency_scores_campaign(self):
        """
        Computes the overall efficiency score for all projects in a campaign
        """
        for _, project in self.campaign.projects.items():
            self.compute_overall_efficiency_scores_project(project)
