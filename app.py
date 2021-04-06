import json
import os
from flask import Flask, request
from solver.rcpsp_solver import solve_rcpsp
from utils.dti_handler import DateTimeIndexParser


app = Flask(__name__)


@app.route("/schedule", methods=["POST"])
def schedule():
    json_msg = request.get_data()

    # Default return message.
    message_dict = {'return_code': '200', 'result': False}

    # Get data from json.
    if json_msg is None:
        message_dict['return_code'] = '5004'
        message_dict['return_info'] = '请求参数为空'
        return json.dumps(message_dict, ensure_ascii=False)

    # Clear last result.
    try:
        os.remove('preview/json/result.json')
    except:
        pass

    # Call algorithm.
    try:
        message_dict['result'] = solve_rcpsp(json_msg, timeout=10)
    except:
        print('Data Error!')
        pass

    return json.dumps(message_dict, ensure_ascii=False)


@app.route("/schedule/dti", methods=["POST"])
def dti():
    json_msg = request.get_data()

    # Default return message.
    message_dict = {'return_code': '200', 'result': False}

    # Get data from json.
    if json_msg is None:
        message_dict['return_code'] = '5004'
        message_dict['return_info'] = '请求参数为空'
        return json.dumps(message_dict, ensure_ascii=False)

    # Call dti handler.
    try:
        data = json.loads(json_msg)
        dti_parser = DateTimeIndexParser(data['start_date'], data['end_date'])
        dti_parser.update(data['start_hour'], data['work_duration'], data['week_mask'])
        dti_parser.gen_json(data['result'])  # ToDo: Can not use gen_json without data_handler.
        message_dict['result'] = True
    except:
        print('Data Error!')
        pass

    return json.dumps(message_dict, ensure_ascii=False)


if __name__ == "__main__":
    app.run(debug=True)