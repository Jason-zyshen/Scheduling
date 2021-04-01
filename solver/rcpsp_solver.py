import os
import time
from collections import defaultdict
from ortools.sat.python import cp_model
from utils.proto_parser import parse_json
from utils.dict2obj import json2obj


class VariableContainer:
    def __init__(self):
        # Container for problem.
        self.resources_list = None
        self.order_list = None
        self.pre_result = None

        # Container for orders.
        self.order_num = None
        self.order_end = dict()
        self.makespan = dict()

        # Container for tasks.
        self.task_names = dict()
        self.task_starts = dict()
        self.task_ends = dict()
        self.duration = dict()
        self.task_gap = defaultdict(list)

        # Containers for per-recipe per task variables.
        self.alternatives_per_task = dict()
        self.presences_per_task = dict()
        self.starts_per_task = dict()
        self.ends_per_task = dict()

        # Containers used to build resources.
        self.intervals_per_resource = defaultdict(list)
        self.demands_per_resource = defaultdict(list)
        self.presences_per_resource = defaultdict(list)
        self.duration_per_resource = defaultdict(list)
        self.workforce_of_res = list()
        self.usage_of_res = list()

        # Containers for results.
        self.result = defaultdict()

    def print_info(self):
        """Print problem info."""

        # suffix = '/Max delay' if self.order_list[0].is_rcpsp_max else ''
        suffix = ''

        res_num = len(self.resources_list)
        task_num = sum([len(order.tasks) for order in self.order_list])
        print('Solving RCPSP%s with %i resources, %i orders and %i tasks' %
              (suffix, res_num, self.order_num, task_num))

    def calculate_horizon(self, problem):
        """Calculate the horizon of the problem."""

        problem.horizon = problem.deadline
        if problem.horizon == -1:  # Naive computation.
            problem.horizon = sum(max(r.duration for r in t.recipes) for t in problem.tasks)
            # if problem.is_rcpsp_max:
            #     for t in problem.tasks:
            #         for sd in t.successor_delays:
            #             for rd in sd.recipe_delays:
            #                 for d in rd.min_delays:
            #                     problem.horizon += abs(d)
        # print('  - horizon = %i' % problem.horizon)

    def initialize_orders(self, data):
        self.order_list = data.orders
        self.resources_list = data.resources
        self.order_num = len(self.order_list)
        self.print_info()

        for o, order in enumerate(self.order_list):
            self.task_starts[o] = {}
            self.task_ends[o] = {}
            self.duration[o] = {}

            self.alternatives_per_task[o] = defaultdict(list)
            self.starts_per_task[o] = defaultdict(list)
            self.ends_per_task[o] = defaultdict(list)
            self.presences_per_task[o] = defaultdict(list)

            self.calculate_horizon(order)

    def store_task_demands(self, order, task, recipe, interval,
                           start=None, end=None, is_present=None):
        """Store task variables and register demands to resources"""

        if not is_present:  # Have only one recipe.
            start = self.task_starts[order][task]
            end = self.task_ends[order][task]
            is_present = 1

        # Store variables.
        self.alternatives_per_task[order][task].append(interval)
        self.starts_per_task[order][task].append(start)
        self.ends_per_task[order][task].append(end)
        self.presences_per_task[order][task].append(is_present)

        # Register intervals in resources.
        for i, resource in enumerate(recipe.resources):
            self.duration_per_resource[resource].append(recipe.duration)
            self.demands_per_resource[resource].append(recipe.demands[i])
            self.intervals_per_resource[resource].append(interval)
            self.presences_per_resource[resource].append(is_present)

    def process_result(self, solver):
        # Print status.
        print(solver.ResponseStats())
        if solver.StatusName() == 'INFEASIBLE':
            print('INFEASIBLE')
            return

        # Process task results.
        print('\n=========== Task Result ===========')
        self.result['tasks'] = {}
        for order in range(self.order_num):
            task_list = list(self.task_starts[order].keys())
            self.result['tasks'][order] = {}
            for task in task_list:
                # print('order_%i task_%i' % (order, task))
                self.result['tasks'][order][task] = {}
                start = solver.Value(self.task_starts[order][task])
                end = solver.Value(self.task_ends[order][task])
                self.result['tasks'][order][task]['start'] = start
                self.result['tasks'][order][task]['end'] = end
                for recipe, presence in enumerate(self.presences_per_task[order][task]):
                    if solver.Value(presence) == 1:
                        task_res = self.order_list[order].tasks[task].recipes[recipe]
                        self.result['tasks'][order][task]['recipe'] = recipe
                        self.result['tasks'][order][task]['duration'] = task_res.duration
                        self.result['tasks'][order][task]['resource'] = {}
                        res_msg = ''
                        for res, demand in zip(task_res.resources, task_res.demands):
                            self.result['tasks'][order][task]['resource'][res] = demand
                            res_msg += ' %ix%i' % (demand, res)

                        print('Task_%i-%i: %i->%i, Mode_%i:' %
                              (order, task, start, end, recipe) + res_msg)
                        break

        # Process resources results.
        print('\n=========== Resource Result ===========')
        self.result['resource'] = {}
        for r, resource in enumerate(self.resources_list):
            capacity = resource.max_capacity
            workforce = solver.Value(self.workforce_of_res[r])
            usage = sum([d * solver.Value(p) for d, p in
                        zip(self.duration_per_resource[r], self.presences_per_resource[r])])
            self.result['resource'][r] = {}
            self.result['resource'][r]['max_capacity'] = capacity
            self.result['resource'][r]['workforce_of_res'] = workforce
            self.result['resource'][r]['usage_of_res'] = usage

            print('Res_%i: %i/%i, Time: %i' % (r, workforce, capacity, usage))


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__solution_count = 0
        self.__start_time = time.time()

    def on_solution_callback(self):
        current_time = time.time()
        objective = self.ObjectiveValue()
        print('Solution %i, time = %f s, objective = %i' %
              (self.__solution_count, current_time - self.__start_time, objective))
        self.__solution_count += 1


def parse_tasks(model, problem, order, variable, available_start):
    o = order
    # Create task variables.
    for t, task in enumerate(problem.tasks):  # sample: problem.tasks[1:-1]
        # t += 1  # Correct the task id.    # sample
        recipes_num = len(task.recipes)

        # Compute duration range.
        min_size = min(recipe.duration for recipe in task.recipes)
        max_size = max(recipe.duration for recipe in task.recipes)

        variable.task_starts[o][t] = model.NewIntVar(0, problem.horizon, 'start_of_task_%i_order_%i' % (t, o))
        variable.task_ends[o][t] = model.NewIntVar(0, problem.horizon, 'end_of_task_%i_order_%i' % (t, o))
        variable.duration[o][t] = model.NewIntVar(min_size, max_size, 'duration_of_task_%i_order_%i' % (t, o))

        if variable.pre_result: # Use the former decision on recipes.
            # Create interval.
            r = variable.pre_result[o][t]['recipe']
            recipe = task.recipes[r]
            interval = model.NewIntervalVar(
                variable.task_starts[o][t], recipe.duration, variable.task_ends[o][t], 'interval_%i_order_%i' % (t, o))
            variable.store_task_demands(o, t, recipe, interval)

        elif recipes_num == 1:  # Only one recipe.
            # Create interval.
            recipe = task.recipes[0]
            interval = model.NewIntervalVar(
                variable.task_starts[o][t], recipe.duration, variable.task_ends[o][t], 'interval_%i_order_%i' % (t, o))
            variable.store_task_demands(o, t, recipe, interval)

        else:  # Mutiple recipes.
            # Create one optional interval per recipe.
            all_recipes = range(recipes_num)
            for r in all_recipes:
                recipe = task.recipes[r]
                is_present = model.NewBoolVar('is_present_t%i_r%i_o%i' % (t, r, o))
                start = model.NewIntVar(0, problem.horizon, 'start_t%i_r%i_o%i' % (t, r, o))
                end = model.NewIntVar(0, problem.horizon, 'end_t%i_r%i_o%i' % (t, r, o))
                interval = model.NewOptionalIntervalVar(start, recipe.duration, end, is_present,
                                                        'interval_t%i_r%i_o%i' % (t, r, o))
                variable.store_task_demands(o, t, recipe, interval, start, end, is_present)

            # Link with optional per-recipe copies.
            for r in all_recipes:
                p = variable.presences_per_task[o][t][r]
                model.Add(variable.task_starts[o][t] == variable.starts_per_task[o][t][r]).OnlyEnforceIf(p)
                model.Add(variable.task_ends[o][t] == variable.ends_per_task[o][t][r]).OnlyEnforceIf(p)
                # model.Add(variable.duration[o][t] == task.recipes[r].duration).OnlyEnforceIf(p)  # It's great, but why??
            model.Add(sum(variable.presences_per_task[o][t]) == 1)

    # Add task available start.  #todo
    # for t in range(len(problem.tasks)):
    #         model.Add(variable.task_starts[o][t] >= available_start[o][t])

    # Add precedences constraints.
    variable.order_end[o] = model.NewIntVar(0, problem.horizon, 'order_%i end' % o)
    variable.makespan[o] = variable.order_end[o] - variable.task_starts[o][0]
    # if problem.is_rcpsp_max:
    #     for t, task in enumerate(problem.tasks):
    #         if len(task.successors) == 0:  # last node
    #             model.Add(variable.task_ends[o][t] <= variable.order_end[o])
    #             continue
    #         for s, successor, in enumerate(task.successors):
    #             if len(task.successor_delays) == 0:  # first node
    #                 break
    #             delay_matrix = task.successor_delays[s]
    #             for m1 in range(len(task.recipes)):
    #                 e1 = variable.ends_per_task[o][t][m1]  # todo: use "starts_per_task" when running sample test_data
    #                 p1 = variable.presences_per_task[o][t][m1]
    #                 for m2 in range(len(problem.tasks[successor].recipes)):
    #                     s2 = variable.starts_per_task[o][successor][m2]
    #                     p2 = variable.presences_per_task[o][successor][m2]
    #                     delay = delay_matrix.recipe_delays[m1].min_delays[m2]
    #                     model.Add(e1 + delay <= s2).OnlyEnforceIf([p1, p2])
    # else:  # Normal dependencies (task ends before the start of successors).
    for t, task in enumerate(problem.tasks):
        if len(task.successors) == 0:  # last node
            model.Add(variable.task_ends[o][t] <= variable.order_end[o])
            continue
        for n in task.successors:
            model.Add(variable.task_ends[o][t] <= variable.task_starts[o][n])


def parse_resource(model, r, resource, variable):
    if resource.max_capacity == -1:
        resource.max_capacity = sum(variable.demands_per_resource[r])

    # Create objective variable.
    variable.workforce_of_res.append(model.NewIntVar(0, resource.max_capacity, 'use_of_res_%i' % r))
    variable.usage_of_res.append(sum([d * p for d, p in zip(variable.duration_per_resource[r],
                                                          variable.presences_per_resource[r])]))

    # Add resource capacity constraints.
    if resource.renewable:
        model.AddCumulative(variable.intervals_per_resource[r],
                            variable.demands_per_resource[r], variable.workforce_of_res[r])
    else:
        model.Add(sum([p * d for p, d in zip(variable.presences_per_resource[r],
                                             variable.demands_per_resource[r])]) <= resource.max_capacity)


def set_objective(model, variable, target, expect=None, res_id=None):
    """
    Optional targets: 'makespan', 'workforce'.
    """

    # Create objective variable.
    if target == 'makespan':
        max_end = max([o.horizon for o in variable.order_list])
        var_end = list(variable.order_end.values())
        end = model.NewIntVar(0, max_end, target)
        model.AddMaxEquality(end, var_end)

        max_makespan = sum([o.horizon for o in variable.order_list])
        var_makespan = sum(variable.makespan.values())

        objective = model.NewIntVar(0, max_makespan + max_end, target)
        model.Add(objective == var_makespan + end)

    # elif target == 'order_makespan':
    #     max_value = sum([o.horizon for o in variable.order_list])
    #     var_value = sum(variable.makespan.values())
    #     objective = model.NewIntVar(0, max_value, target)
    #     model.Add(objective == var_value)
    
    # elif target == 'total_makespan':
    #     max_value = max([o.horizon for o in variable.order_list])
    #     var_value = list(variable.order_end.values())
    #     objective = model.NewIntVar(0, max_value, target)
    #     model.AddMaxEquality(objective, var_value)

    elif target == 'workforce':
        max_value = variable.resources_list[res_id].max_capacity if res_id else sum(
            r.max_capacity for r in variable.resources_list)
        var_value = variable.workforce_of_res[res_id] if res_id else sum(variable.workforce_of_res)
        objective = model.NewIntVar(0, max_value, target)
        model.Add(objective == var_value)
    else:
        print('Objective is invalid! Search for feasible result.\n')
        return

    if expect:
        model.Add(objective <= expect)
        print('Minimize %s to %d' % (objective.Name(), expect))
    else:
        model.Minimize(objective)
        print('Searching for minimum %s' % objective.Name())


def load_xwy():
    """
    DEPRECATED.
    """
    data_dir = 'test_data/xwy_test'
    all_resources = parse_json('res.json', file_dir=data_dir, keys=['resources'])
    order_list = [parse_json('order_%d.json' % o, file_dir=data_dir) for o in range(54)]

    class Input():
        def __init__(self, order_list, all_resources):
            self.orders = order_list
            self.resources = all_resources.resources

    data = Input(order_list, all_resources)

    return data


def solve_rcpsp(input, obj_list=None, timeout=None, pre_result=None):
    """Parse and solve a given RCPSP problem in proto/json format."""

    data = json2obj(input)

    # set available start time for tasks.
    available_start = {}  # todo: {order_id: {task_id: start_time}}

    # Initialize the model.
    model = cp_model.CpModel()
    variable = VariableContainer()
    variable.initialize_orders(data)
    if pre_result:
        variable.pre_result = pre_result

    # Parse test_data to constraints.
    for o, order in enumerate(data.orders):
        parse_tasks(model, order, o, variable, available_start)
    for r, resource in enumerate(data.resources):
        parse_resource(model, r, resource, variable)


    # Objective.
    set_objective(model, variable, 'makespan')
    if obj_list:
        for obj in obj_list:
            set_objective(model, variable, obj['type'], obj['expect'])

    # Solve model.
    # model.AddDecisionStrategy(var_list, cp_model.CHOOSE_FIRST, cp_model.SELECT_MIN_VALUE)
    solver = cp_model.CpSolver()
    # solver.StringParameters = "numSearchWorkers:4"
    # solver.parameters.search_branching = cp_model.FIXED_SEARCH  # Force the solver to follow the decision strategy exactly.
    if timeout:
        solver.parameters.max_time_in_seconds = timeout

    # Print result.
    solution_printer = SolutionPrinter()
    solver.SolveWithSolutionCallback(model, solution_printer)
    variable.process_result(solver)

    return variable.result['tasks']


def main():
    # obj_list = [{'type': 'makespan', 'expect': None}]
    result = solve_rcpsp(timeout=10)


if __name__ == '__main__':
    main()


