import json
import numpy as np
import pandas as pd
from solver.rcpsp_solver import solve_rcpsp
from utils.dict2obj import df2dict
from utils.dti_handler import DateTimeIndexParser


def cal_duration(row):
    amount = row.amount if np.isnan(row['fix_amount']) else row.fix_amount
    if row.speed != 0:
        duration = row.fix_time + amount / row.speed
    else:
        duration = row.fix_time
    return int(duration)


def check_row(row):
    return len(row['only_product'])==0 or row['product'] in row['only_product']


# Load test_data set.
input = 'data/asd_test.xlsx'
order = pd.read_excel(input, sheet_name='order')
product = pd.read_excel(input, sheet_name='product')
process = pd.read_excel(input, sheet_name='process')
resource = pd.read_excel(input, sheet_name='resource')

# Generate task test_data.
task_df = pd.merge(order, product, how='outer', on='product')
task_df = pd.merge(task_df, process, how='outer', on='process')
task_df['fix_time'] = task_df['fix_time'] * 60  # Convert hours to minutes.
task_df['speed'] = task_df['speed'].fillna(0)
task_df['only_product'] = task_df['only_product'].fillna('')
task_df['duration'] = task_df.apply(cal_duration, axis=1)
task_df['check'] = task_df.apply(check_row, axis=1)

# Group process
groups = task_df[task_df['group_process'].notnull()]
index = ['order_id', 'product', 'amount', 'deadline', 'group_process', 'resource_type', 'resource_demand']
aggregation = {'duration': sum, 'process_id': min, 'next_process': max, 'mode': min}
group_tasks_1 = groups[groups['fix_amount'].isnull()].groupby(by=index).agg(aggregation).reset_index()
group_tasks_2 = groups[groups['fix_amount'].notnull()].groupby(by=index).agg(aggregation).reset_index()
group_tasks = pd.concat([group_tasks_1, group_tasks_2]).rename(columns={'group_process': 'process'})

column_list = ['order_id', 'product', 'amount', 'deadline', 'process', 'process_id', 'next_process',
               'mode', 'duration', 'resource_type', 'resource_demand']
tasks = task_df[task_df['check'] & task_df['group_process'].isnull()][column_list]
output = pd.concat([tasks, group_tasks]).sort_values(by=['order_id', 'process_id'])

# Append resource
# ToDo

output.to_excel('test_data/asd_test/output.xlsx')