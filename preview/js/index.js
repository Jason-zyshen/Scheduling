window.onload = () => {
    let taskData2
    let originTaskData
    let resourceDataList = [];
    const url = 'json/result.json';
    const request = new XMLHttpRequest();
    request.open('get', url);
    request.send(null);
    request.onload = function () {
        if (request.status === 200) {
            taskData2 = JSON.parse(request.responseText);
//            const listK = [25,26]
//            taskData2.data = taskData2.data.filter(item => listK.indexOf(item.id) !== -1 || listK.indexOf(item.parent) !== -1)
//            console.log(taskData2.data.filter(item => listK.indexOf(item.id) !== -1 || listK.indexOf(item.parent) !== -1),)
            originTaskData = JSON.parse(request.responseText);
            JSON.parse(request.responseText).resourceData.forEach(item => {
                resourceDataList.push({
                    id: item.res_id.toString(),
                    name: item.res_name,
                    max: item.maxCapacity
                });
            })
            loadCharts();
        }
    }
    function loadCharts() {
        console.log(resourceDataList);
        const column = [
            {
                name: "text",
                label: "任务名",
                tree: true,
                width: "*"
            },
            {
                name: "start_date",
                label: "开始时间",
                align: "center",
                width: 130
            },
            {
                name: "resources",
                label: "资源",
                align: "center",
                width: 60,
                template: function (task) {
                    let keys = task.resource ? Object.keys(task.resource) : []
                    const filter = resourceDataList.filter(item => keys.indexOf(item.id) !== -1);
                    const keysStr = filter.map(item => item.name);
                    return "<div class='owner-label'>" + keysStr.join(' | ') + "</div>";
                }
            },
            {
                name: "duration",
                label: "时长",
                align: "center",
                width: 80
            }
        ];
        const resourceConfig = {
            columns: [
                {
                    name: "name", label: "资源名", tree: true, template: function (resource) {
                        const filter = resourceDataList.filter(item => item.id === resource.text);
                        return filter[0].name;
                    }
                },
                {
                    name: "number", label: "数量", template: function (resource) {
                        const filter = resourceDataList.filter(item => item.id === resource.text);
                        return filter[0].max;
                    }
                },
                {
                    name: "duration", label: "时长", template: function (resource) {
                        let tasks;
                        tasks = taskData2.data;
                        let totalDuration = 0;
                        for (let i = 0; i < tasks.length; i++) {
                            if (tasks[i].resource && tasks[i].resource[resource.text]) {
                                totalDuration += tasks[i].duration;
                            }
                        }
                        return totalDuration || 0;
                    }
                }
            ]
        };
        const resourcesList = [];

        gantt.attachEvent("onGanttReady", function () {
            let tooltips = gantt.ext.tooltips;

            gantt.templates.tooltip_text = function (start, end, task) {
                let str = "<b>任务名:</b> " + task.text + "<br/>" +
                    "<b>开始时间:</b>" + dayjs(start).format('YYYY-MM-DD HH:mm') + "<br/>" +
                    "<b>结束时间:</b> " + dayjs(end).format('YYYY-MM-DD HH:mm') + "<br/>" +
                    "<b>交期:</b> " + dayjs(task.deadline).format('YYYY-MM-DD HH:mm') + "<br/>" +
                    "<b>时长:</b> " + task.duration || 0;
                if (task.resource) {
                    Object.keys(task.resource).forEach(item => {
                        const filter = resourceDataList.filter(r => r.id === item);
                        str += "<br/>" + "<b>" + filter[0].name + ":</b> " + task.resource[item]
                    })
                }
                return str;
            };


            tooltips.tooltipFor({
                selector: ".gantt_scale_cell",
                html: function (event, node) {
                    let relativePosition = gantt.utils.dom.getRelativeEventPosition(event, gantt.$task_scale);
                    return gantt.templates.tooltip_date_format(gantt.dateFromPos(relativePosition.x));
                }
            });

            tooltips.tooltipFor({
                selector: ".gantt_resource_marker",
                html: function (event, node) {
                    let dataElement = node.querySelector("[data-recource-tasks]");
                    let ids = JSON.parse(dataElement.getAttribute("data-recource-tasks"));

                    let date = gantt.templates.parse_date(dataElement.getAttribute("data-cell-date"));
                    let resourceId = dataElement.getAttribute("data-resource-id");


                    let store = gantt.getDatastore("resource");
                    const filter = resourceDataList.filter(item => item.id === store.getItem(resourceId).text);
                    let html = [
                        "<b>" + filter[0].name + "</b>" + ", " + gantt.templates.tooltip_date_format(date),
                        "",
                        ids.map(function (id, index) {
                            let task = gantt.getTask(id);
                            let taskParent = gantt.getTask(task.parent);
                            let assignenment = gantt.getResourceAssignments(resourceId, task.id);
                            let amount = "";
                            if (assignenment[0]) {
                                amount = " (" + task.duration + "min) ";
                            }
                            const filter = resourcesList.filter(item => item.id === resourceId);
                            return taskParent.text + " [" + task.resource[filter[0].text] + "]" + ": " + amount + " " + task.text;
                        }).join("<br>")
                    ].join("<br>");

                    return html;
                }
            });
        });
        gantt.i18n.setLocale("cn");
        gantt.plugins({tooltip: true});
        gantt.config.columns = column;
        gantt.config.work_time = true;
        gantt.setWorkTime({hours: ["9:00-17:00"]})
        gantt.setWorkTime({day: 0, hours: ["9:00-17:00"]})
        gantt.setWorkTime({day: 6, hours: ["9:00-17:00"]})
        gantt.config.date_format = "%Y-%m-%d %H:%i";
        gantt.config.date_grid = "%Y-%m-%d %H:%i";
        gantt.config.min_column_width = 20;
        gantt.config.duration_step = 1;
        gantt.config.scale_height = 75;
        gantt.config.time_step = 1;
        gantt.config.min_column_width = 60;
        gantt.config.skip_off_time = true;
        gantt.config.scales = [
            {unit: "hour", step: 1, format: "%g %a"},   //todo
            {
                unit: "day", step: 1, format: (date) => {
                    const formatFunc = gantt.date.date_to_str('%Y-%m-%d')
                    return formatFunc(date);
                }
            },
            // {unit: "minute", step: minuteStep, format: "%i"}
        ];
        gantt.templates.timeline_cell_class = function (task, date) {
            if (!gantt.isWorkTime(date))
                return "week_end";
            return "";
        };
        gantt.templates.resource_cell_class = function (start_date, end_date, resource, tasks) {
            let css = [];
            css.push("resource_marker");
            if (tasks.length <= 1) {
                css.push("workday_ok");
            } else {
                css.push("workday_over");
            }
            return css.join(" ");
        };
        gantt.templates.resource_cell_value = function (start_date, end_date, resource, tasks) {
            const tasksDiffTimes = [];
            tasks.forEach(item => {
                let diffTime = 0;
                let status;
                let statusStart = compareDate(start_date, item.start_date);
                let statusEnd = compareDate(end_date, item.end_date);
                let startDate;
                let endDate;
                let startNumber;
                let endNumber;
                if (statusStart && !statusEnd) {
                    status = 'outIn';
                    diffTime = 60;
                    startDate = start_date;
                    endDate = end_date;
                    startNumber = 0;
                    endNumber = 60;
                }
                if (statusStart && statusEnd) {
                    status = 'start';
                    diffTime = dayjs(item.end_date).diff(dayjs(start_date), 'm');
                    startDate = start_date;
                    endDate = item.end_date;
                    startNumber = 0;
                    endNumber = diffTime;
                }
                if (!statusStart && !statusEnd) {
                    status = 'end';
                    diffTime = dayjs(end_date).diff(dayjs(item.start_date), 'm');
                    startDate = item.start_date;
                    endDate = end_date;
                    startNumber = dayjs(item.start_date).diff(dayjs(start_date), 'm');
                    endNumber = 60;
                }
                if (!statusStart && statusEnd) {
                    status = 'inIn';
                    diffTime = dayjs(item.end_date).diff(dayjs(item.start_date), 'm');
                    startDate = item.start_date;
                    endDate = item.end_date;
                    startNumber = dayjs(item.start_date).diff(dayjs(start_date), 'm');
//                    endNumber = 60 - dayjs(end_date).diff(dayjs(item.end_date), 'm');
                    endNumber = dayjs(item.end_date).diff(dayjs(start_date), 'm')
                }
                tasksDiffTimes.push({
                    startS: dayjs(item.start_date).format('YYYY-MM-DD HH:mm:ss'),
                    start: dayjs(start_date).format('YYYY-MM-DD HH:mm:ss'),
                    endS: dayjs(item.end_date).format('YYYY-MM-DD HH:mm:ss'),
                    end: dayjs(end_date).format('YYYY-MM-DD HH:mm:ss'),
                    startDate: dayjs(startDate).format('YYYY-MM-DD HH:mm:ss'),
                    endDate: dayjs(endDate).format('YYYY-MM-DD HH:mm:ss'),
                    sourceNumber: item.resource[resource.text],
                    startNumber,
                    endNumber,
                    diffTime,
                    status
                });
            })
            const countList = [];
            tasksDiffTimes.forEach(diff1 => {
                const list = [];
                const list2 = [];
                tasksDiffTimes.forEach(diff2 => {
                    if (diff1.startNumber >= diff2.startNumber && diff1.endNumber <= diff2.endNumber) {
                        list.push(diff2.sourceNumber)
                        list2.push({diff1, diff2})
                    }
                })
                console.log(list2);
                countList.push(list.reduce((a, b) => a + b, 0))
            })
            countList.sort((a, b) => {
                if (a < b) return 1
                return -1
            })
            const max = countList[0];

            let color = 'rgb(114,187,90)'
            let tasksIds = "data-recource-tasks='" + JSON.stringify(tasks.map(function (task) {
                return task.id
            })) + "'";
            const filter = resourceDataList.filter(item => resource.text === item.id);
            if (filter[0].max < max) color = 'red'
            let resourceId = "data-resource-id='" + resource.id + "'";
            let dateAttr = "data-cell-date='" + gantt.templates.format_date(start_date) + "'";
            return `<div ${tasksIds} ${resourceId} ${dateAttr} style=\'background: ${color}\'>${max}</div>`;
        };
        gantt.locale.labels.section_owner = "资源";
        gantt.config.resource_store = "resource";
        gantt.config.duration_unit = "minute";
        gantt.config.resource_property = "resources";
        gantt.config.order_branch = true;
        gantt.config.open_tree_initially = false;
        gantt.config.layout = {
            css: "gantt_container",
            rows: [
                {
                    cols: [
                        {view: "grid", group: "grids", scrollY: "scrollVer"},
                        {resizer: true, width: 1},
                        {view: "timeline", scrollX: "scrollHor", scrollY: "scrollVer"},
                        {view: "scrollbar", id: "scrollVer", group: "vertical"}
                    ],
                    gravity: 2
                },
                {resizer: true, width: 1},
                {
                    config: resourceConfig,
                    cols: [
                        {view: "resourceGrid", group: "grids", width: 435, scrollY: "resourceVScroll"},
                        {resizer: true, width: 1},
                        {view: "resourceTimeline", scrollX: "scrollHor", scrollY: "resourceVScroll"},
                        {view: "scrollbar", id: "resourceVScroll", group: "vertical"}
                    ],
                    gravity: 1
                },
                {view: "scrollbar", id: "scrollHor"}
            ]
        };
        gantt.$resourcesStore = gantt.createDatastore({
            name: gantt.config.resource_store,
            type: "treeDatastore",
            initItem: function (item) {
                item.parent = item.parent || gantt.config.root_id;
                item[gantt.config.resource_property] = item.parent;
                item.open = true;
                return item;
            }
        });
        gantt.init("gantt_here");
        taskData2.data.forEach((item) => {
            const resource = [];
            item.resources = [];
            if (item.resource) {
                const keys = Object.keys(item.resource);
                keys.forEach((key, keyIndex) => {
                    const texts = resourcesList.map(item => item.text);
                    resource.push({name: key, number: item.resource[key]})
                    if (texts.indexOf(key) === -1) {
                        resourcesList.push({id: `${key}_${keyIndex}`, text: key, parent: null, resource})
                    }
                    const texts2 = resourcesList.map(item => item.text);
                    item.resources.push({resource_id: resourcesList[texts2.indexOf(key)].id, value: item.resource[key]})
                });
            }
            delete item.duration
        })
        gantt.$resourcesStore.parse(resourcesList);
        gantt.parse(taskData2);
    }
}

function compareDate(date1,date2) {
    let oDate1 = new Date(date1);
    let oDate2 = new Date(date2);
    if (oDate1.getTime() >= oDate2.getTime()) {
        return true; //第一个大
    } else {
        return false; //第二个大
    }
}


function formatDate(item) {
    const start_date = dayjs(taskData2.today).add(item.start_date, taskData2.timestep).format('YYYY-MM-DD HH:mm:ss')
    判断当前日期是否为工作时间
    if(gantt.isWorkTime(new Date(start_date))) {
        return start_date
    } else {
        // 返回最接近的工作日期
        const closeWorkDate = dayjs(gantt.getClosestWorkTime({date: new Date(start_date), dir:"future"})).format('YYYY-MM-DD HH:mm:ss');
        const filterP = originTaskData.data.filter(d => d.id === item.parent);
        const filterC = originTaskData.data.filter(d => d.id === item.id);
        if (!filterP.length) {
            return closeWorkDate;
        } else {
            const filterCDate = dayjs(originTaskData.today).add(filterC[0].start_date, taskData2.timestep).format('YYYY-MM-DD HH:mm:ss');
            const filterPDate = dayjs(originTaskData.today).add(filterP[0].start_date, taskData2.timestep).format('YYYY-MM-DD HH:mm:ss');
            const diffTime = dayjs(filterCDate).diff(dayjs(filterPDate), taskData2.timestep);
            return dayjs(closeWorkDate).add(diffTime, taskData2.timestep).format("YYYY-MM-DD HH:mm:ss");
        }
    }

}
