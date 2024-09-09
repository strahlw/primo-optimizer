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
from itertools import combinations

# Installed libs
from haversine import Unit, haversine
from pyomo.common.config import (
    Bool,
    ConfigDict,
    ConfigValue,
    In,
    IsInstance,
    NonNegativeFloat,
    NonNegativeInt,
    document_kwargs_from_configdict,
)
from pyomo.environ import SolverFactory

# User-defined libs
from primo.data_parser import WellData
from primo.opt_model.model_with_clustering import PluggingCampaignModel
from primo.utils import get_solver
from primo.utils.clustering import perform_clustering
from primo.utils.domain_validators import InRange, validate_mobilization_cost
from primo.utils.raise_exception import raise_exception

LOGGER = logging.getLogger(__name__)


# pylint: disable = protected-access, attribute-defined-outside-init
# pylint: disable = logging-fstring-interpolation
class OptModelInputs:
    """
    Assembles all the necessary inputs for the optimization model.
    """

    # Container for storing and performaing domain validation
    # of the inputs of the optimization model.
    # ConfigValue automatically performs domain validation.
    CONFIG = ConfigDict()
    CONFIG.declare(
        "well_data",
        ConfigValue(
            domain=IsInstance(WellData),
            doc="WellData object containing the entire dataset.",
        ),
    )
    CONFIG.declare(
        "total_budget",
        ConfigValue(
            domain=NonNegativeFloat,
            doc="Total budget for plugging [in USD]",
        ),
    )
    CONFIG.declare(
        "mobilization_cost",
        ConfigValue(
            domain=validate_mobilization_cost,
            doc="Cost of plugging wells [in USD].",
        ),
    )
    CONFIG.declare(
        "perc_wells_in_dac",
        ConfigValue(
            domain=InRange(0, 100),
            doc="Minimum percentage of wells in disadvantaged communities",
        ),
    )
    CONFIG.declare(
        "threshold_distance",
        ConfigValue(
            default=10.0,
            domain=NonNegativeFloat,
            doc="Maximum distance [in miles] allowed between wells",
        ),
    )
    CONFIG.declare(
        "max_wells_per_owner",
        ConfigValue(
            domain=NonNegativeInt,
            doc="Maximum number of wells per owner",
        ),
    )
    CONFIG.declare(
        "max_cost_project",
        ConfigValue(
            domain=NonNegativeFloat,
            doc="Maximum cost per project [in USD]",
        ),
    )
    CONFIG.declare(
        "max_size_project",
        ConfigValue(
            domain=NonNegativeInt,
            doc="Maximum number of wells admissible per project",
        ),
    )
    CONFIG.declare(
        "num_wells_model_type",
        ConfigValue(
            default="multicommodity",
            domain=In(["multicommodity", "incremental"]),
            doc="Choice of formulation for modeling number of wells",
        ),
    )
    CONFIG.declare(
        "model_nature",
        ConfigValue(
            default="linear",
            domain=In(["linear", "quadratic", "aggregated_linear"]),
            doc="Nature of the optimization model: MILP or MIQCQP",
        ),
    )
    CONFIG.declare(
        "lazy_constraints",
        ConfigValue(
            default=False,
            domain=Bool,
            doc="If True, some constraints will be added as lazy constraints",
        ),
    )

    # Using Pyomo's ConfigDict for domain validation.
    @document_kwargs_from_configdict(CONFIG)
    def __init__(self, **kwargs):
        # Update the values of all the inputs
        # ConfigDict handles KeyError, other input errors, and domain errors
        LOGGER.info("Processing optimization model inputs.")
        self.config = self.CONFIG(kwargs)

        # Raise an error if the essential inputs are not provided
        wd = self.config.well_data
        if None in [wd, self.config.total_budget, self.config.mobilization_cost]:
            msg = (
                "One or more essential input arguments in [well_data, total_budget, "
                "mobilization_cost] are missing while instantiating the object. "
                "WellData object containing information on all wells, the total budget, "
                "and the mobilization cost are essential inputs for the optimization model. "
            )
            raise_exception(msg, ValueError)

        # Raise an error if priority scores are not calculated.
        if "Priority Score [0-100]" not in wd:
            msg = (
                "Unable to find priority scores in the data. Compute the scores using the "
                "compute_priority_scores method."
            )
            raise_exception(msg, ValueError)

        # Construct campaign candidates
        # Step 1: Perform clustering, Should distance_threshold be a user argument?
        # FIXME: Are distance_threshold and threshold_distance related?
        perform_clustering(wd, distance_threshold=10.0)

        # Step 2: Identify list of wells belonging to each cluster
        # Structure: {cluster_1: [index_1, index_2,..], cluster_2: [], ...}
        col_names = wd._col_names
        set_clusters = set(wd.data[col_names.cluster])
        self.campaign_candidates = {
            cluster: list(wd.data[wd.data[col_names.cluster] == cluster].index)
            for cluster in set_clusters
        }

        # Step 3: Construct pairwise-metrics between wells in each cluster.
        # Structure: {cluster: {(index_1, index_2): distance_12, ...}...}
        self.pairwise_distance = {
            cluster: self._distance_matrix(self.campaign_candidates[cluster])
            for cluster in set_clusters
        }
        self.pairwise_age_difference = {
            cluster: self._range_matrix(self.campaign_candidates[cluster], "age")
            for cluster in set_clusters
        }
        self.pairwise_depth_difference = {
            cluster: self._range_matrix(self.campaign_candidates[cluster], "depth")
            for cluster in set_clusters
        }

        # Construct owner well count data
        operator_list = set(wd.data[col_names.operator_name])
        self.owner_well_count = {owner: [] for owner in operator_list}
        for well in wd:
            # {Owner 1: [(c1, i2), (c1, i3), (c4, i7), ...], ...}
            # Key => Owner name, Tuple[0] => cluster, Tuple[1] => index
            self.owner_well_count[wd.data.loc[well, col_names.operator_name]].append(
                (wd.data.loc[well, col_names.cluster], well)
            )

        # NOTE: Attributes _opt_model and _solver are defined in
        # build_optimization_model and solve_model methods, respectively.

        LOGGER.info("Finished optimization model inputs.")

    @property
    def get_total_budget(self):
        """Returns scaled total budget [in million USD]"""
        # Optimization model uses scaled total budget value to avoid numerical issues
        return self.config.total_budget / 1e6

    @property
    def get_mobilization_cost(self):
        """Returns scaled mobilization cost [in million USD]"""
        # Optimization model uses Scaled mobilization costs to avoid numerical issues
        return {
            num_wells: cost / 1e6
            for num_wells, cost in self.config.mobilization_cost.items()
        }

    @property
    def get_max_cost_project(self):
        """Returns scaled maximum cost of the project [in million USD"""
        if self.config.max_cost_project is None:
            return None

        return self.config.max_cost_project / 1e6

    def _distance_matrix(self, index: list):
        """Returns pairwise distance for a given set of wells"""
        wd = self.config.well_data
        df = wd.data
        latitude = wd._col_names.latitude
        longitude = wd._col_names.longitude
        return {
            (j, k): haversine(
                (df.loc[j, latitude], df.loc[j, longitude]),
                (df.loc[k, latitude], df.loc[k, longitude]),
                unit=Unit.MILES,
            )
            for j, k in combinations(index, 2)
        }

    def _range_matrix(self, index: list, column: str):
        """
        Returns pairwise difference of a column of interest
        for a given set of wells

        index : list
            List of rows/indices in the WellData object

        column : str
            Allowed columns are "age", "depth"
        """
        wd = self.config.well_data
        df = wd.data
        column = getattr(wd._col_names, column)
        return {
            (j, k): abs(df.loc[j, column] - df.loc[k, column])
            for j, k in combinations(index, 2)
        }

    def build_optimization_model(self):
        """Builds the optimization model"""
        LOGGER.info("Beginning to construct the optimization model.")
        self._opt_model = PluggingCampaignModel(self)
        return self._opt_model

    def solve_model(self, **kwargs):
        """Solves the optimization"""

        # Adding support for pool search if gurobi_persistent is available
        # To get n-best solutions, pass pool_search_mode = 2 and pool_size = n
        pool_search_mode = kwargs.pop("pool_search_mode", 0)
        pool_size = kwargs.pop("pool_size", 10)

        # If a solver is specified, use it.
        if "solver" in kwargs:
            solver = get_solver(**kwargs)

        else:
            # Otherwise, auto-detect solver in order of priority
            for sol in ("gurobi_persistent", "gurobi", "scip", "glpk", "highs"):
                solver = SolverFactory(sol)
                if solver.available(exception_flag=False):
                    LOGGER.info(
                        f"Optimization solver is not specified. "
                        f"Using {sol} as the optimization solver."
                    )
                    self._solver = solver
                    break

        if solver.name == "gurobi_persistent":
            # For persistent solvers, model instance need to be set manually
            solver.set_instance(self._opt_model)
            solver.set_gurobi_param("PoolSearchMode", pool_search_mode)
            solver.set_gurobi_param("PoolSolutions", pool_size)

        # Solve the optimization problem
        solver.solve(self._opt_model)

        return self._opt_model.get_optimal_campaign()

    def get_solution_pool(self):
        """Extracts solutions from the solution pool"""
        solver = self._solver
        pm = self._opt_model  # This is the pyomo model
        gm = solver._solver_model  # This is the gurobipy model
        # Get Pyomo var to Gurobipy var map.
        # Gurobi vars can be accessed as py_to_gp[<pyomo var>]
        py_to_gp = solver._pyomo_var_to_solver_var_map

        # Return if the pool search mode is not 2
        if gm.Params.PoolSearchMode != 2 or solver.name != "gurobi_persistent":
            LOGGER.warning("Pool-search was not used for the solve.")
            return None

        # Number of solutions found
        num_solutions = gm.SolCount
        solution_pool = {}
        wd = self.config.well_data  # Well data

        for i in range(num_solutions):
            gm.Params.SolutionNumber = i

            optimal_campaign = {}
            plugging_cost = {}

            for c in pm.set_clusters:
                blk = pm.cluster[c]
                if py_to_gp[blk.select_cluster].Xn < 0.05:
                    # Cluster c is not chosen, so continue
                    continue

                # Wells in cluster c are chosen
                optimal_campaign[c] = []
                plugging_cost[c] = py_to_gp[blk.plugging_cost].Xn
                for w in blk.set_wells:
                    if py_to_gp[blk.select_well[w]].Xn > 0.95:
                        # Well w is chosen, so store it in the dict
                        optimal_campaign[c].append(w)

            # Uncomment the following lines after result_parser is merged
            # solution_pool[i + 1] = OptimalCampaign(
            #     wd=wd, clusters_dict=optimal_campaign, plugging_cost=plugging_cost
            # )
            solution_pool[i + 1] = (optimal_campaign, plugging_cost)

        return solution_pool
