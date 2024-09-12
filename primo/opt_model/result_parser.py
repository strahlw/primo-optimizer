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

# User-defined libs
from primo.data_parser import WellData
from primo.utils.project_information_utils import ProjectDescriptor

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
        self._df = wd.data.loc[index]
        self._col_names = wd._col_names
        col_names = self._col_names

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
        self.project_info.print_project_info()

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

    @property
    def num_wells_near_hospitals(self):
        """Returns number of wells that are near hospitals"""
        col_name = self._col_names.hospitals
        if col_name is None:
            return INFO_UNAVAILABLE

        return len(self._df[self._df[col_name] > 0].index)

    @property
    def num_wells_near_schools(self):
        """Returns number of wells that are near schools"""
        col_name = self._col_names.schools
        if col_name is None:
            return INFO_UNAVAILABLE

        return len(self._df[self._df[col_name] > 0].index)


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
