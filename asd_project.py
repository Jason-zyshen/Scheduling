import json
import numpy as np
import pandas as pd
from solver.rcpsp_solver import solve_rcpsp
from utility.dict_obj_df import df2dict
from utility.data_parser import DateTimeIndexParser, json_parser


def cal_duration(row):
    amount = row.amount if np.isnan(row['fix_amount']) else row.fix_amount
    if row.speed != 0:
        duration = row.fix_time + amount / row.speed
    else:
        duration = row.fix_time
    return int(duration)


def check_row(row):
    return len(row['only_product'])==0 or row['product'] in row['only_product']


def process_data(data_dir):
    data_dir = 'test_data/xwy_test'

    # Load test_data.
    tasks_file = 'test_data/xwy-quilt-task.xlsx'
    resource_file = 'test_data/xwy-quilt-resource.xlsx'
    tasks_df = pd.read_excel(tasks_file)
    resource_df = pd.read_excel(resource_file)

    # Parse resources.
    res_dict = dict()
    res_dict['resources'] = resource_df[['maxCapacity', 'renewable']].to_dict(orient='records')
    with open(data_dir+'/res.json', 'w') as f:
        f.write(json.dumps(res_dict))

    # Initiate time parser.
    start_date = '2021-02-21'
    week_mask = "Mon Tue Wed Thu Fri Sat Sun"
    end_date = tasks_df['deadline'].max()
    dti_parser = DateTimeIndexParser(start_date, end_date)
    dti_parser.update(weekmask=week_mask)

    # Parse tasks.
    orders = tasks_df.order_id.unique()
    for o in orders:
        # Parse task test_data
        order_data = dict()
        task_list = list()
        order_tasks = tasks_df[tasks_df.order_id == o]
        tasks = order_tasks.task_id.unique()
        for t in tasks:
            task_data = dict()
            task_df = order_tasks[order_tasks.task_id == t]
            task_data['successors'] = eval(task_df['successors'].unique().tolist()[0])
            task_data['recipes'] = task_df[['duration', 'resources', 'demands']].to_dict(orient='records')
            for recipe in task_data['recipes']:
                recipe['resources'] = eval(recipe['resources'])
                recipe['demands'] = eval(recipe['demands'])
            task_list.append(task_data)
        order_data['tasks'] = task_list
        ddl = order_tasks['deadline'].iloc[0]
        order_data['deadline'] = dti_parser.dti2step(ddl)

        # Dump to json
        with open(data_dir+'/order_%d.json' % o, 'w') as f:
            f.write(json.dumps(order_data))

    # Generate name dict
    output = dict()
    output['today'] = str(dti_parser.start_datetime)
    output['timestep'] = 'm'
    output['resourceData'] = resource_df.to_dict('records')
    output['ddl'] = dict(tasks_df[['order_id', 'deadline']].values)

    df = tasks_df[['order_id', 'task_id', 'task_name']]
    col = ['order_id', 'task_id']
    output['task'] = df2dict(df, col)

    return output, dti_parser


def main():
    data_dir = 'test_data/xwy_test'
    output, dti = process_data(data_dir)
    result = solve_rcpsp(data_dir, timeout=10)
    json_parser(output, result, dti)


if __name__ == '__main__':
    main()

# Load test_data set.
input = 'test_data/asd_test/asd_test.xlsx'
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