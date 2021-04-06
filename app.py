import json
import os
from flask import Flask, request
from solver.rcpsp_solver import solve_rcpsp
from utils.dti_handler import DateTimeIndexParser


app = Flask(__name__)


@app.route("/schedule", methods=["POST"])
def schedule():

    # Clear last result.
    try:
        os.remove('preview/json/index.json')
    except:
        pass

    # Default return message.
    message_dict = {'return_code': '200', 'result': False}

    # Get data from json.
    if request.get_data() is None:
        message_dict['return_code'] = '5004'
        message_dict['return_info'] = '请求参数为空'
        return json.dumps(message_dict, ensure_ascii=False)

    data = request.get_data()

    # Call algorithm.
    try:
        result = solve_rcpsp(data, timeout=10)
        message_dict['result'] = result
    except:
        print('Data Error!')
        pass

    return json.dumps(message_dict, ensure_ascii=False)


@app.route("/dti2step", methods=["POST"])
def dti():

    # Default return message.
    message_dict = {'return_code': '200', 'result': False}

    # Get data from json.
    if request.get_data() is None:
        message_dict['return_code'] = '5004'
        message_dict['return_info'] = '请求参数为空'
        return json.dumps(message_dict, ensure_ascii=False)

    data = json.loads(request.get_data())

    # Call dti handler.
    try:
        # Initialize dit parser.
        dti_parser = DateTimeIndexParser(data['start_date'], data['end_date'])
        dti_parser.update(data['start_hour'], data['work_duration'], data['week_mask'])

        # Convert datetime to time steps.
        step = dti_parser.dti2step(data['datetime'])
        message_dict['result'] = {'step': step}
    except:
        print('Data Error!')
        pass

    return json.dumps(message_dict, ensure_ascii=False)


def dti_test_client():
    import requests
    data = {'start_date': '2021-02-21',
            'end_date': '2021-03-24',
            'start_hour': '10:00',
            'work_duration': 10,
            'week_mask': 'Mon Tue Wed Thu Fri Sat',
            'datetime': '2021-02-23',  # or '2021-02-23 09:00:00'
            }
    myurl = "http://127.0.0.1:5000/dti2step"

    r = requests.post(myurl, data=json.dumps(data))
    result = json.loads(r.text)['result']
    print(result)


if __name__ == "__main__":
    app.run(debug=True)