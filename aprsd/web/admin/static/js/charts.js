var packet_list = {};

window.chartColors = {
    red: 'rgb(255, 99, 132)',
    orange: 'rgb(255, 159, 64)',
    yellow: 'rgb(255, 205, 86)',
    green: 'rgb(26, 181, 77)',
    blue: 'rgb(54, 162, 235)',
    purple: 'rgb(153, 102, 255)',
    grey: 'rgb(201, 203, 207)',
    black: 'rgb(0, 0, 0)',
    lightcoral: 'rgb(240,128,128)',
    darkseagreen: 'rgb(143, 188,143)'

};

function size_dict(d){c=0; for (i in d) ++c; return c}

function start_charts() {
    Chart.scaleService.updateScaleDefaults('linear', {
        ticks: {
            min: 0
        }
    });

    packets_chart = new Chart($("#packetsChart"), {
        label: 'APRS Packets',
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Packets Sent',
                borderColor: window.chartColors.lightcoral,
                data: [],
            },
            {
                label: 'Packets Recieved',
                borderColor: window.chartColors.darkseagreen,
                data: [],
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            title: {
                display: true,
                text: 'APRS Packets',
            },
            scales: {
                x: {
                    type: 'timeseries',
                    offset: true,
                    ticks: {
                        major: { enabled: true },
                        fontStyle: context => context.tick.major ? 'bold' : undefined,
                        source: 'data',
                        maxRotation: 0,
                        autoSkip: true,
                        autoSkipPadding: 75,
                    }
                }
            }
        }
    });

    message_chart = new Chart($("#messageChart"), {
        label: 'Messages',
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Messages Sent',
                borderColor: window.chartColors.lightcoral,
                data: [],
            },
            {
                label: 'Messages Recieved',
                borderColor: window.chartColors.darkseagreen,
                data: [],
            },
            {
                label: 'Ack Sent',
                borderColor: window.chartColors.purple,
                data: [],
            },
            {
                label: 'Ack Recieved',
                borderColor: window.chartColors.black,
                data: [],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            title: {
                display: true,
                text: 'APRS Messages',
            },
            scales: {
                x: {
                    type: 'timeseries',
                    offset: true,
                    ticks: {
                        major: { enabled: true },
                        fontStyle: context => context.tick.major ? 'bold' : undefined,
                        source: 'data',
                        maxRotation: 0,
                        autoSkip: true,
                        autoSkipPadding: 75,
                    }
                }
            }
        }
    });

    email_chart = new Chart($("#emailChart"), {
        label: 'Email Messages',
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Sent',
                borderColor: window.chartColors.lightcoral,
                data: [],
            },
            {
                label: 'Recieved',
                borderColor: window.chartColors.darkseagreen,
                data: [],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            title: {
                display: true,
                text: 'Email Messages',
            },
            scales: {
                x: {
                    type: 'timeseries',
                    offset: true,
                    ticks: {
                        major: { enabled: true },
                        fontStyle: context => context.tick.major ? 'bold' : undefined,
                        source: 'data',
                        maxRotation: 0,
                        autoSkip: true,
                        autoSkipPadding: 75,
                    }
                }
            }
        }
    });

    memory_chart = new Chart($("#memChart"), {
        label: 'Memory Usage',
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Peak Ram usage',
                borderColor: window.chartColors.red,
                data: [],
            },
            {
                label: 'Current Ram usage',
                borderColor: window.chartColors.blue,
                data: [],
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            title: {
                display: true,
                text: 'Memory Usage',
            },
            scales: {
                x: {
                    type: 'timeseries',
                    offset: true,
                    ticks: {
                        major: { enabled: true },
                        fontStyle: context => context.tick.major ? 'bold' : undefined,
                        source: 'data',
                        maxRotation: 0,
                        autoSkip: true,
                        autoSkipPadding: 75,
                    }
                }
            }
        }
    });
}


function addData(chart, label, newdata) {
    chart.data.labels.push(label);
    chart.data.datasets.forEach((dataset) => {
        dataset.data.push(newdata);
    });
    chart.update();
}

function updateDualData(chart, label, first, second) {
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(first);
    chart.data.datasets[1].data.push(second);
    chart.update();
}
function updateQuadData(chart, label, first, second, third, fourth) {
    chart.data.labels.push(label);
    chart.data.datasets[0].data.push(first);
    chart.data.datasets[1].data.push(second);
    chart.data.datasets[2].data.push(third);
    chart.data.datasets[3].data.push(fourth);
    chart.update();
}

function update_stats( data ) {
    our_callsign = data["APRSDStats"]["callsign"];
    $("#version").text( data["APRSDStats"]["version"] );
    $("#aprs_connection").html( data["aprs_connection"] );
    $("#uptime").text( "uptime: " + data["APRSDStats"]["uptime"] );
    const html_pretty = Prism.highlight(JSON.stringify(data, null, '\t'), Prism.languages.json, 'json');
    $("#jsonstats").html(html_pretty);
    short_time = data["time"].split(/\s(.+)/)[1];
    packet_list = data["PacketList"]["packets"];
    updateDualData(packets_chart, short_time, data["PacketList"]["sent"], data["PacketList"]["received"]);
    updateQuadData(message_chart, short_time, packet_list["MessagePacket"]["tx"], packet_list["MessagePacket"]["rx"],
     packet_list["AckPacket"]["tx"], packet_list["AckPacket"]["rx"]);
    updateDualData(email_chart, short_time, data["EmailStats"]["sent"], data["EmailStats"]["recieved"]);
    updateDualData(memory_chart, short_time, data["APRSDStats"]["memory_peak"], data["APRSDStats"]["memory_current"]);
}
