import json
from collections import defaultdict


class obj: 
    def __init__(self, dict1): 
        self.__dict__.update(dict1)


def dict2obj(dict1):
    return json.loads(json.dumps(dict1), object_hook=obj)


def json2obj(json_data):
    return json.loads(json_data, object_hook=obj)


def df2dict(df, col):
    d = defaultdict(dict)
    for i, row in df.iterrows():
        d[row[col[0]]][row[col[1]]] = row.drop(col).to_dict()
    return dict(d)