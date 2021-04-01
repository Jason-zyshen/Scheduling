import os
import json
from google.protobuf.json_format import MessageToDict, ParseDict
from ortools.data import pywraprcpsp
from ortools.data import rcpsp_pb2


def parse_proto(proto_file, data_dir=None):
    """Parse proto file to dictionary or json file"""
    rcpsp_parser = pywraprcpsp.RcpspParser()
    rcpsp_parser.ParseFile(proto_file)
    proto_problem = rcpsp_parser.Problem()
    dict_problem = MessageToDict(proto_problem)

    if data_dir:
        os.mkdir(data_dir)
        with open(data_dir + '/order_0.json', 'w') as f:
            json.dump(dict_problem, f)
        with open(data_dir + '/res.json', 'w') as f:
            json.dump(dict_problem, f)

    return dict_problem


def parse_json(json_file, file_dir=None, keys=None, hint=False):
    """Parse json to proto object"""

    problem_message = rcpsp_pb2.RcpspProblem()
    if file_dir:
        json_file = file_dir + '/' + json_file
    with open(json_file, 'r') as f:
        dict_problem = json.loads(f.read())

    if hint:
        print('Available Keys: ' + str(list(dict_problem.keys())))

    if keys:
        dict_problem = {k: dict_problem[k] for k in keys}

    problem = ParseDict(dict_problem, problem_message)
    return problem
