import json
import pandas as pd


class DateTimeIndexParser():
    def __init__(self, start_date, end_date):
        self.work_period = ['09:00', '17:00']
        self.work_duration = 8
        self.weekmask = "Mon Tue Wed Thu Fri"
        self.cbh = 'BH'
        self.start = start_date
        self.end = end_date + pd.Timedelta('1 day')
        self.dti = pd.date_range(self.start, self.end, freq=self.cbh)
        self.start_datetime = self.dti[0]

    def update(self, work_period=None, weekmask=None):
        if work_period:
            self.work_period = work_period
        elif weekmask:
            self.weekmask = weekmask
        self.cbh = pd.offsets.CustomBusinessHour(start=self.work_period[0],
                                                 end=self.work_period[1],
                                                 weekmask=self.weekmask)
        self.dti = pd.date_range(self.start, self.end, freq=self.cbh)
        cal_duration = lambda x: int(x[1].split(':')[0]) - int(x[0].split(':')[0])
        self.work_duration = cal_duration(self.work_period)

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

    def dti2step(self, dt, day_end=False):
        """
        Convert datetime to time steps.
        :param dt: str, datetime. e.g. 2021-02-21 or 2021-02-21 09:00:00
        :param day_end: bool, if the deadline is the end of the day.
        :return: int, time steps.
        """

        if dt.hour == 0:  # Datetime only has date.
            dt = dt + pd.Timedelta(self.work_period[day_end] + ':00')  # Add time to the date.
        step = self.dti.get_loc(dt) * 60
        return step


def json_parser(output, result, dti_parser):
    output['test_data'] = list()
    for o, order in zip(result.keys(), result.values()):
        o += 1
        data = dict()
        data['id'] = o
        data['text'] = 'order_%d' % o
        data['start_date'] = min([d['start'] for d in list(order.values())])
        data['end_date'] = max([d['end'] for d in list(order.values())])
        data['duration'] = data['end_date'] - data['start_date']
        data['resource'] = None
        data['deadline'] = str(output['ddl'][o-1])
        data['parent'] = 0
        output['test_data'].append(data)

        for t, task in zip(order.keys(), order.values()):
            data = dict()
            data['id'] = o * 100 + t
            data['text'] = output['task'][o-1][t]['task_name']
            data['start_date'] = task['start']
            data['end_date'] = task['end']
            data['duration'] = task['duration']
            data['resource'] = task['resource']
            data['parent'] = o
            output['test_data'].append(data)

    for data in output['test_data']:
        data['start_date'] = str(dti_parser.step2dti(data['start_date']))
        data['end_date'] = str(dti_parser.step2dti(data['end_date'], task_end=True))

    with open('../preview/json/index.json', 'w') as f:
        output.pop('ddl')
        output.pop('task')
        f.write(json.dumps(output))

    print('\nGenerate json file.\n\n')