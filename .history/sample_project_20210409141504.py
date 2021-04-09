import requests
import json
import pandas as pd
from solver.rcpsp_solver import solve_rcpsp
from utils.dti_handler import DateTimeIndexParser


def post(data, server="http://127.0.0.1:5000", page='/schedule'):
    """
    Post data to server and get response.
    :param data: dict.
    :param server:
    :param page:
    :return: dict.
    """

    with open('data%s_input.json' % page, 'w') as f:
        f.write(json.dumps(data))

    data = json.dumps(data)
    r = requests.post(server + page, data=data)
    result = json.loads(r.text)['result']

    with open('data%s_output.json' % page, 'w') as f:
        f.write(json.dumps(result))

    return result


def run():
    # Set calendar.
    calendar = {'start_date': '2021-02-21',
                'end_date': '2022-01-01',
                'start_hour': '10:00',
                'work_duration': 8,
                'week_mask': 'Mon Tue Wed Thu Fri Sat Sun',
                }
    dti_parser = DateTimeIndexParser(
        calendar['start_date'], calendar['end_date'])
    dti_parser.update(weekmask=calendar['week_mask'])

    # Load data set.
    # input_data = dti_parser.data_handler(tasks_df, resource_df)
    with open('data/schedule_input.json', 'r') as f:
        input_data = json.loads(f.read())

    # Solve problem.
    output_data = post(input_data)  # Call remote solver
    # result = solve_rcpsp(json.loads(input_data), timeout=10)  # Use local solver.

    # Format result.
    data = calendar
    data['result'] = output_data
    result = post(data, page='/dti')
    with open('preview/json/result.json', 'w') as f:
        f.write(json.dumps(result))


if __name__ == "__main__":
    run()
