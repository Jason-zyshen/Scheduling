import json
import pandas as pd
from utils.dict2obj import df2dict


class DateTimeIndexParser():
    def __init__(self, start_date, end_date):
        self.start_hour = '09:00'
        self.end_hour = '17:00'
        self.work_duration = 8
        self.weekmask = 'Mon Tue Wed Thu Fri'
        self.cbh = 'BH'
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date) + pd.Timedelta('1 day')
        self.dti = pd.date_range(self.start_date, self.end_date, freq=self.cbh)
        self.start_datetime = self.dti[0]
        self.data = None
        self.output = dict()

    def cal_end_hour(self):
        s = self.start_hour
        d = self.work_duration
        e = min(int(s[0:2]) + d, 24)  # 24h
        self.end_hour = str(e) + s[2:5]

    def update(self, start_hour=None, work_duration=None, weekmask=None):
        if weekmask:
            self.weekmask = weekmask
        if start_hour:
            self.start_hour = start_hour
        if work_duration:
            self.work_duration = work_duration

        self.cal_end_hour()
        self.cbh = pd.offsets.CustomBusinessHour(start=self.start_hour,
                                                 end=self.end_hour,
                                                 weekmask=self.weekmask)
        self.dti = pd.date_range(self.start_date, self.end_date, freq=self.cbh)

    def step2dti(self, step, task_end=False):
        """
        Convert time steps to real world date and time.
        :param step: int, time steps in solver.
        :param task_end: bool, if it's the end of a task or order.
        :return: str, real world date and time.
        """

        hours = int(step / 60)
        minutes = step % 60
        last_minute = (hours % self.work_duration == 0) and (hours > 0)
        if task_end and last_minute:  # Consider the last minute of the day
            hours = int(step / 60) - 1
            minutes = 60

        delta_min = pd.Timedelta("%i min" % minutes)
        dt = self.dti[hours] + delta_min
        return dt

    def dti2step(self, dt):
        """
        Convert datetime to time steps.
        :param dt: str, datetime. e.g. 2021-02-21 or 2021-02-21 09:00:00
        :return: int, time steps in minutes.
        """

        dt = pd.Timestamp(dt)
        if dt.hour == 0:  # Datetime only has date.
            dt = dt + pd.Timedelta(self.start_hour + ':00')  # Add time to the date.
        step = self.dti.get_loc(dt) * 60
        return step

    def data_handler(self, tasks_df, resource_df):
        """
        Convert input data into solver format. Based on xwy project.
        :param tasks_df:
        :param resource_df:
        :return:
        """

        # Parse tasks.
        data = dict()
        data['orders'] = list()
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
            order_data['deadline'] = self.dti2step(ddl)

            data['orders'].append(order_data)

        # Parse resources.
        data['resources'] = resource_df[['max_capacity', 'renewable']].to_dict(orient='records')
        self.data = data
        with open('data/tmp.json', 'w') as f:
            f.write(json.dumps(data))

        # Save problem info to object.
        df = tasks_df[['order_id', 'task_id', 'task_name']]
        col = ['order_id', 'task_id']
        self.output['task'] = df2dict(df, col)
        self.output['ddl'] = dict(tasks_df[['order_id', 'deadline']].values)
        self.output['resourceData'] = resource_df.to_dict('records')
        self.output['timestep'] = 'm'

    def gen_json(self, result, path='preview/json/'):
        """
        Convert result to json file.
        :param result:
        :return:
        """

        self.output['today'] = str(self.start_datetime)
        self.output['data'] = list()
        for o, order in zip(result.keys(), result.values()):
            o = int(o)
            o += 1
            data = dict()
            data['id'] = o
            data['text'] = 'order_%d' % o
            data['start_date'] = min([d['start'] for d in list(order.values())])
            data['end_date'] = max([d['end'] for d in list(order.values())])
            data['duration'] = data['end_date'] - data['start_date']
            data['resource'] = None
            data['deadline'] = str(self.output['ddl'][o-1])
            data['parent'] = 0
            self.output['data'].append(data)

            for t, task in zip(order.keys(), order.values()):
                t = int(t)
                data = dict()
                data['id'] = o * 100 + t
                data['text'] = self.output['task'][o-1][t]['task_name']
                data['start_date'] = task['start']
                data['end_date'] = task['end']
                data['duration'] = task['duration']
                data['resource'] = task['resource']
                data['parent'] = o
                self.output['data'].append(data)

        for data in self.output['data']:
            data['start_date'] = str(self.step2dti(data['start_date']))
            data['end_date'] = str(self.step2dti(data['end_date'], task_end=True))

        with open(path + 'index.json', 'w') as f:
            self.output.pop('ddl')
            self.output.pop('task')
            f.write(json.dumps(self.output))

        print('\njson file generated, please check the browser.')