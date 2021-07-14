var packet_list = {};

window.chartColors = {
    red: 'rgb(255, 99, 132)',
    orange: 'rgb(255, 159, 64)',
    yellow: 'rgb(255, 205, 86)',
    green: 'rgb(26, 181, 77)',
    blue: 'rgb(54, 162, 235)',
    purple: 'rgb(153, 102, 255)',
    grey: 'rgb(201, 203, 207)',
    black: 'rgb(0, 0, 0)'
};

function size_dict(d){c=0; for (i in d) ++c; return c}

function start_charts() {
    Chart.scaleService.updateScaleDefaults('linear', {
        ticks: {
            min: 0
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

    message_chart = new Chart($("#messageChart"), {
        label: 'Messages',
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Messages Sent',
                borderColor: window.chartColors.green,
                data: [],
            },
            {
                label: 'Messages Recieved',
                borderColor: window.chartColors.yellow,
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
                borderColor: window.chartColors.green,
                data: [],
            },
            {
                label: 'Recieved',
                borderColor: window.chartColors.yellow,
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
    $("#version").text( data["stats"]["aprsd"]["version"] );
    $("#aprsis").text( "APRS-IS Server: " + data["stats"]["aprs-is"]["server"] );
    $("#uptime").text( "uptime: " + data["stats"]["aprsd"]["uptime"] );
    const html_pretty = Prism.highlight(JSON.stringify(data, null, '\t'), Prism.languages.json, 'json');
    $("#jsonstats").html(html_pretty);
    short_time = data["time"].split(/\s(.+)/)[1];
    updateQuadData(message_chart, short_time, data["stats"]["messages"]["sent"], data["stats"]["messages"]["recieved"], data["stats"]["messages"]["ack_sent"], data["stats"]["messages"]["ack_recieved"]);
    updateDualData(email_chart, short_time, data["stats"]["email"]["sent"], data["stats"]["email"]["recieved"]);
    updateDualData(memory_chart, short_time, data["stats"]["aprsd"]["memory_peak"], data["stats"]["aprsd"]["memory_current"]);
}


function update_packets( data ) {
    var packetsdiv = $("#packetsDiv");
    //nuke the contents first, then add to it.
    if (size_dict(packet_list) == 0 && size_dict(data) > 0) {
        packetsdiv.html('')
    }
    jQuery.each(data, function(i, val) {
        if ( packet_list.hasOwnProperty(i) == false ) {
            packet_list[i] = val;
            var d = new Date(i*1000).toLocaleDateString("en-US")
            var t = new Date(i*1000).toLocaleTimeString("en-US")
            if (val.hasOwnProperty('from') == false) {
                from = val['fromcall']
                title_id = 'title_tx'
            } else {
                from = val['from']
                title_id = 'title_rx'
            }
            var from_to = d + " " + t + "&nbsp;&nbsp;&nbsp;&nbsp;" + from + " > "

            if (val.hasOwnProperty('addresse')) {
                from_to = from_to + val['addresse']
            } else if (val.hasOwnProperty('tocall')) {
                from_to = from_to + val['tocall']
            } else if (val.hasOwnProperty('format') && val['format'] == 'mic-e') {
                from_to =  from_to + "Mic-E"
            }

            from_to = from_to + "&nbsp;&nbsp;-&nbsp;&nbsp;" + val['raw']

            json_pretty = Prism.highlight(JSON.stringify(val, null, '\t'), Prism.languages.json, 'json');
            pkt_html = '<div class="title" id="' + title_id + '"><i class="dropdown icon"></i>' + from_to + '</div><div class="content"><p class="transition hidden"><pre class="language-json">' + json_pretty + '</p></p></div>'
            packetsdiv.prepend(pkt_html);
        }
    });

    $('.ui.accordion').accordion('refresh');

    // Update the count of messages shown
    cnt = size_dict(packet_list);
    console.log("packets list " + cnt)
    $('#packets_count').html(cnt);

    const html_pretty = Prism.highlight(JSON.stringify(data, null, '\t'), Prism.languages.json, 'json');
    $("#packetsjson").html(html_pretty);
}


function start_update() {

    (function statsworker() {
            $.ajax({
                url: "/stats",
                type: 'GET',
                dataType: 'json',
                success: function(data) {
                    update_stats(data);
                },
                complete: function() {
                    setTimeout(statsworker, 10000);
                }
            });
    })();

    (function packetsworker() {
        $.ajax({
            url: "/packets",
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                update_packets(data);
            },
            complete: function() {
                setTimeout(packetsworker, 10000);
            }
        });
    })();
}
