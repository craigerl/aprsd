var packet_list = {};

var tx_data = [];
var rx_data = [];

var packet_types_data = {};

var mem_current = []
var mem_peak = []


function start_charts() {
    console.log("start_charts() called");
    // Initialize the echarts instance based on the prepared dom
    create_packets_chart();
    create_packets_types_chart();
    create_messages_chart();
    create_ack_chart();
    create_memory_chart();
}


function create_packets_chart() {
    // The packets totals TX/RX chart.
    pkt_c_canvas = document.getElementById('packetsChart');
    packets_chart = echarts.init(pkt_c_canvas);

    // Specify the configuration items and data for the chart
    var option = {
      title: {
          text: 'APRS Packet totals'
      },
      legend: {},
      tooltip : {
        trigger: 'axis'
      },
      toolbox: {
        show : true,
        feature : {
           mark : {show: true},
           dataView : {show: true, readOnly: true},
           magicType : {show: true, type: ['line', 'bar']},
           restore : {show: true},
           saveAsImage : {show: true}
        }
      },
      calculable : true,
      xAxis: { type: 'time' },
      yAxis: { },
      series: [
          {
             name: 'tx',
             type: 'line',
             smooth: true,
             color: 'red',
             encode: {
               x: 'timestamp',
               y: 'tx' // refer sensor 1 value
             }
          },{
             name: 'rx',
             type: 'line',
             smooth: true,
             encode: {
               x: 'timestamp',
               y: 'rx'
          }
      }]
    };

    // Display the chart using the configuration items and data just specified.
    packets_chart.setOption(option);
}


function create_packets_types_chart() {
    // The packets types chart
    pkt_types_canvas = document.getElementById('packetTypesChart');
    packet_types_chart = echarts.init(pkt_types_canvas);

    // The series and data are built and updated on the fly
    // as packets come in.
    var option = {
      title: {
          text: 'Packet Types'
      },
      legend: {},
      tooltip : {
        trigger: 'axis'
      },
      toolbox: {
        show : true,
        feature : {
           mark : {show: true},
           dataView : {show: true, readOnly: true},
           magicType : {show: true, type: ['line', 'bar']},
           restore : {show: true},
           saveAsImage : {show: true}
        }
      },
      calculable : true,
      xAxis: { type: 'time' },
      yAxis: { },
    }

    packet_types_chart.setOption(option);
}


function create_messages_chart() {
    msg_c_canvas = document.getElementById('messagesChart');
    message_chart = echarts.init(msg_c_canvas);

    // Specify the configuration items and data for the chart
    var option = {
      title: {
          text: 'Message Packets'
      },
      legend: {},
      tooltip: {
        trigger: 'axis'
      },
      toolbox: {
        show: true,
        feature: {
           mark : {show: true},
           dataView : {show: true, readOnly: true},
           magicType : {show: true, type: ['line', 'bar']},
           restore : {show: true},
           saveAsImage : {show: true}
        }
      },
      calculable: true,
      xAxis: { type: 'time' },
      yAxis: { },
      series: [
          {
             name: 'tx',
             type: 'line',
             smooth: true,
             color: 'red',
             encode: {
               x: 'timestamp',
               y: 'tx' // refer sensor 1 value
             }
          },{
             name: 'rx',
             type: 'line',
             smooth: true,
             encode: {
               x: 'timestamp',
               y: 'rx'
          }
      }]
    };

    // Display the chart using the configuration items and data just specified.
    message_chart.setOption(option);
}

function create_ack_chart() {
    ack_canvas = document.getElementById('acksChart');
    ack_chart = echarts.init(ack_canvas);

    // Specify the configuration items and data for the chart
    var option = {
      title: {
          text: 'Ack Packets'
      },
      legend: {},
      tooltip: {
        trigger: 'axis'
      },
      toolbox: {
        show: true,
        feature: {
           mark : {show: true},
           dataView : {show: true, readOnly: false},
           magicType : {show: true, type: ['line', 'bar']},
           restore : {show: true},
           saveAsImage : {show: true}
        }
      },
      calculable: true,
      xAxis: { type: 'time' },
      yAxis: { },
      series: [
          {
             name: 'tx',
             type: 'line',
             smooth: true,
             color: 'red',
             encode: {
               x: 'timestamp',
               y: 'tx' // refer sensor 1 value
             }
          },{
             name: 'rx',
             type: 'line',
             smooth: true,
             encode: {
               x: 'timestamp',
               y: 'rx'
          }
      }]
    };

    ack_chart.setOption(option);
}

function create_memory_chart() {
    ack_canvas = document.getElementById('memChart');
    memory_chart = echarts.init(ack_canvas);

    // Specify the configuration items and data for the chart
    var option = {
      title: {
          text: 'Memory Usage'
      },
      legend: {},
      tooltip: {
        trigger: 'axis'
      },
      toolbox: {
        show: true,
        feature: {
           mark : {show: true},
           dataView : {show: true, readOnly: false},
           magicType : {show: true, type: ['line', 'bar']},
           restore : {show: true},
           saveAsImage : {show: true}
        }
      },
      calculable: true,
      xAxis: { type: 'time' },
      yAxis: { },
      series: [
          {
             name: 'current',
             type: 'line',
             smooth: true,
             color: 'red',
             encode: {
               x: 'timestamp',
               y: 'current' // refer sensor 1 value
             }
          },{
             name: 'peak',
             type: 'line',
             smooth: true,
             encode: {
               x: 'timestamp',
               y: 'peak'
          }
      }]
    };

    memory_chart.setOption(option);
}




function updatePacketData(chart, time, first, second) {
    tx_data.push([time, first]);
    rx_data.push([time, second]);
    option = {
        series: [
          {
            name: 'tx',
            data: tx_data,
          },
          {
            name: 'rx',
            data: rx_data,
          }
        ]
    }
    chart.setOption(option);
}

function updatePacketTypesData(time, typesdata) {
    //The options series is created on the fly each time based on
    //the packet types we have in the data
    var series = []

    for (const k in typesdata) {
        tx = [time, typesdata[k]["tx"]]
        rx = [time, typesdata[k]["rx"]]

        if (packet_types_data.hasOwnProperty(k)) {
            packet_types_data[k]["tx"].push(tx)
            packet_types_data[k]["rx"].push(rx)
        } else {
            packet_types_data[k] = {'tx': [tx], 'rx': [rx]}
        }
    }
}

function updatePacketTypesChart() {
  series = []
  for (const k in packet_types_data) {
      entry = {
          name: k+"tx",
          data: packet_types_data[k]["tx"],
          type: 'line',
          smooth: true,
          encode: {
            x: 'timestamp',
            y: k+'tx' // refer sensor 1 value
          }
      }
      series.push(entry)
      entry = {
          name: k+"rx",
          data: packet_types_data[k]["rx"],
          type: 'line',
          smooth: true,
          encode: {
            x: 'timestamp',
            y: k+'rx' // refer sensor 1 value
          }
      }
      series.push(entry)
  }

  option = {
      series: series
  }
  console.log(option)
  packet_types_chart.setOption(option);
}

function updateTypeChart(chart, key)  {
    //Generic function to update a packet type chart
    if (! packet_types_data.hasOwnProperty(key)) {
        return;
    }

    if (! packet_types_data[key].hasOwnProperty('tx')) {
        return;
    }
    var option = {
        series: [{
            name: "tx",
            data: packet_types_data[key]["tx"],
        },
        {
            name: "rx",
            data: packet_types_data[key]["rx"]
        }]
    }

   chart.setOption(option);
}

function updateMemChart(time, current, peak) {
    mem_current.push([time, current]);
    mem_peak.push([time, peak]);
    option = {
        series: [
          {
            name: 'current',
            data: mem_current,
          },
          {
            name: 'peak',
            data: mem_peak,
          }
        ]
    }
    memory_chart.setOption(option);
}

function updateMessagesChart() {
    updateTypeChart(message_chart, "MessagePacket")
}

function updateAcksChart() {
    updateTypeChart(ack_chart, "AckPacket")
}

function update_stats( data ) {
    console.log(data);
    our_callsign = data["stats"]["aprsd"]["callsign"];
    $("#version").text( data["stats"]["aprsd"]["version"] );
    $("#aprs_connection").html( data["aprs_connection"] );
    $("#uptime").text( "uptime: " + data["stats"]["aprsd"]["uptime"] );
    const html_pretty = Prism.highlight(JSON.stringify(data, null, '\t'), Prism.languages.json, 'json');
    $("#jsonstats").html(html_pretty);

    t = Date.parse(data["time"]);
    ts = new Date(t);
    updatePacketData(packets_chart, ts, data["stats"]["packets"]["sent"], data["stats"]["packets"]["received"]);
    updatePacketTypesData(ts, data["stats"]["packets"]["types"]);
    updatePacketTypesChart();
    updateMessagesChart();
    updateAcksChart();
    updateMemChart(ts, data["stats"]["aprsd"]["memory_current"], data["stats"]["aprsd"]["memory_peak"]);
    //updateQuadData(message_chart, short_time, data["stats"]["messages"]["sent"], data["stats"]["messages"]["received"], data["stats"]["messages"]["ack_sent"], data["stats"]["messages"]["ack_recieved"]);
    //updateDualData(email_chart, short_time, data["stats"]["email"]["sent"], data["stats"]["email"]["recieved"]);
    //updateDualData(memory_chart, short_time, data["stats"]["aprsd"]["memory_peak"], data["stats"]["aprsd"]["memory_current"]);
}
