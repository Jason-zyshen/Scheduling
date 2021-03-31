import os
import json
from utility.proto_parser import parse_json
from google.protobuf.json_format import MessageToDict


data_dir = 'test_data/xwy_test'
file_num = len(os.listdir(data_dir))
sample = MessageToDict(parse_json('res.json', file_dir=data_dir, keys=['resources']))
order_list = [MessageToDict(parse_json('order_%d.json' % o, file_dir=data_dir)) for o in range(54)]
sample['orders']= order_list

with open('data/sample.json', 'w') as f:
    f.write(json.dumps(sample))