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


def call_server():
    """
    POST data to algorithm api and receive result from algorithm server.
    :return: result: Dict
    """

    json_file = 'data/tmp.json'
    myurl = "http://127.0.0.1:5000/schedule"

    with open(json_file, 'r') as f:
        data = json.dumps(json.loads(f.read()))

    r = requests.post(myurl, data=data)
    result = json.loads(r.text)['result']

    return result


def run(offline=False):
    # Load data set.
    tasks_df, resource_df = load_xwy()

    # Set problem calendar.
    start_date = '2021-02-21'
    week_mask = "Mon Tue Wed Thu Fri Sat Sun"
    end_date = str(tasks_df['deadline'].max())[:10]
    dti_parser = DateTimeIndexParser(start_date, end_date)
    dti_parser.update(weekmask=week_mask)
    dti_parser.data_handler(tasks_df, resource_df)

    # Solve problem.
    if offline:
        data = json.dumps(dti_parser.data)
        result = solve_rcpsp(data, timeout=10)
    else:
        result = call_server()

    # Update data to frontend.
    dti_parser.gen_json(result)


if __name__ == "__main__":
    run()