import requests
import json
import pandas as pd
from solver.rcpsp_solver import solve_rcpsp
from utils.dti_handler import DateTimeIndexParser


# todo: add config file.


def load_xwy():
    """
    Load test data set for xwy project.
    :return: DataFrame for tasks and resources.
    """
    file = 'data/xwy_test.xlsx'
    tasks_df = pd.read_excel(file, sheet_name='orders')
    resource_df = pd.read_excel(file, sheet_name='resources')

    return tasks_df, resource_df


def post(data, server="http://127.0.0.1:5000", page='/schedule'):
    """
    Post data to server and get response.
    :param data: dict.
    :param server:
    :param page:
    :return: dict.
    """

    data = json.dumps(data)
    r = requests.post(server + page, data=data)
    result = json.loads(r.text)['result']

    return result


def run():
    # Set calendar.
    calendar = {'start_date': '2021-02-21',
                'end_date': '2022-01-01',
                'start_hour': '10:00',
                'work_duration': 8,
                'week_mask': 'Mon Tue Wed Thu Fri Sat Sun',
                }
    dti_parser = DateTimeIndexParser(calendar['start_date'], calendar['end_date'])
    dti_parser.update(weekmask=calendar['week_mask'])

    # Load data set.
    tasks_df, resource_df = load_xwy()
    data = dti_parser.data_handler(tasks_df, resource_df)

    # Solve problem.
    # result = solve_rcpsp(json.loads(data), timeout=10)  # Use local solver.
    data['result'] = post(data)  # Call remote solver
    dti_parser.gen_json(data['result'])


if __name__ == "__main__":
    run()