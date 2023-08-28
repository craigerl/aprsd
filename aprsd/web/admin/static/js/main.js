// watchlist is a dict of ham callsign => symbol, packets
var watchlist = {};
var our_callsign = "";

function aprs_img(item, x_offset, y_offset) {
    var x = x_offset * -16;
    if (y_offset > 5) {
        y_offset = 5;
    }
    var y = y_offset * -16;
    var loc = x + 'px '+ y + 'px'
    item.css('background-position', loc);
}

function show_aprs_icon(item, symbol) {
    var offset = ord(symbol) - 33;
    var col = Math.floor(offset / 16);
    var row = offset % 16;
    //console.log("'" + symbol+"'   off: "+offset+"  row: "+ row + "   col: " + col)
    aprs_img(item, row, col);
}

function ord(str){return str.charCodeAt(0);}


function update_watchlist( data ) {
        // Update the watch list
    var watchdiv = $("#watchDiv");
    var html_str = '<table class="ui celled striped table"><thead><tr><th>HAM Callsign</th><th>Age since last seen by APRSD</th></tr></thead><tbody>'
    watchdiv.html('')
    jQuery.each(data["stats"]["aprsd"]["watch_list"], function(i, val) {
        html_str += '<tr><td class="collapsing"><img id="callsign_'+i+'" class="aprsd_1"></img>' + i + '</td><td>' + val["last"] + '</td></tr>'
    });
    html_str += "</tbody></table>";
    watchdiv.append(html_str);

    jQuery.each(watchlist, function(i, val) {
        //update the symbol
        var call_img = $('#callsign_'+i);
        show_aprs_icon(call_img, val['symbol'])
    });
}

function update_watchlist_from_packet(callsign, val) {
    if (!watchlist.hasOwnProperty(callsign)) {
        watchlist[callsign] = {
            "symbol": '[',
            "packets": {},
        }
    } else {
        if (val.hasOwnProperty('symbol')) {
            //console.log("Updating symbol for "+callsign + " to "+val["symbol"])
            watchlist[callsign]["symbol"] = val["symbol"]
        }
    }
    if (watchlist[callsign]["packets"].hasOwnProperty(val['ts']) == false) {
        watchlist[callsign]["packets"][val['ts']]= val;
    }
    //console.log(watchlist)
}

function update_seenlist( data ) {
    var seendiv = $("#seenDiv");
    var html_str = '<table class="ui celled striped table">'
    html_str    += '<thead><tr><th>HAM Callsign</th><th>Age since last seen by APRSD</th>'
    html_str    += '<th>Number of packets RX</th></tr></thead><tbody>'
    seendiv.html('')
    var seen_list = data["stats"]["aprsd"]["seen_list"]
    var len = Object.keys(seen_list).length
    $('#seen_count').html(len)
    jQuery.each(seen_list, function(i, val) {
        html_str += '<tr><td class="collapsing">'
        html_str += '<img id="callsign_'+i+'" class="aprsd_1"></img>' + i + '</td>'
        html_str += '<td>' + val["last"] + '</td>'
        html_str += '<td>' + val["count"] + '</td></tr>'
    });
    html_str += "</tbody></table>";
    seendiv.append(html_str);
}

function update_plugins( data ) {
    var plugindiv = $("#pluginDiv");
    var html_str = '<table class="ui celled striped table"><thead><tr>'
    html_str +=      '<th>Plugin Name</th><th>Plugin Enabled?</th>'
    html_str +=      '<th>Processed Packets</th><th>Sent Packets</th>'
    html_str +=      '<th>Version</th>'
    html_str +=    '</tr></thead><tbody>'
    plugindiv.html('')

    var plugins = data["stats"]["plugins"];
    var keys = Object.keys(plugins);
    keys.sort();
    for (var i=0; i<keys.length; i++) { // now lets iterate in sort order
        var key = keys[i];
        var val = plugins[key];
        html_str += '<tr><td class="collapsing">' + key + '</td>';
        html_str += '<td>' + val["enabled"] + '</td><td>' + val["rx"] + '</td>';
        html_str += '<td>' + val["tx"] + '</td><td>' + val["version"] +'</td></tr>';
    }
    html_str += "</tbody></table>";
    plugindiv.append(html_str);
}

function update_packets( data ) {
    var packetsdiv = $("#packetsDiv");
    //nuke the contents first, then add to it.
    if (size_dict(packet_list) == 0 && size_dict(data) > 0) {
        packetsdiv.html('')
    }
    jQuery.each(data, function(i, val) {
        pkt = JSON.parse(val);

        update_watchlist_from_packet(pkt['from_call'], pkt);
        if ( packet_list.hasOwnProperty(pkt['timestamp']) == false ) {
            // Store the packet
            packet_list[pkt['timestamp']] = pkt;
            //ts_str = val["timestamp"].toString();
            //ts = ts_str.split(".")[0]*1000;
            ts = pkt['timestamp'] * 1000;
            var d = new Date(ts).toLocaleDateString();
            var t = new Date(ts).toLocaleTimeString();
            var from_call = pkt.from_call;
            if (from_call == our_callsign) {
                title_id = 'title_tx';
            } else {
                title_id = 'title_rx';
            }
            var from_to = d + " " + t + "&nbsp;&nbsp;&nbsp;&nbsp;" + from_call + " > "

            if (val.hasOwnProperty('addresse')) {
                from_to = from_to + pkt['addresse']
            } else if (pkt.hasOwnProperty('to_call')) {
                from_to = from_to + pkt['to_call']
            } else if (pkt.hasOwnProperty('format') && pkt['format'] == 'mic-e') {
                from_to =  from_to + "Mic-E"
            }

            from_to = from_to + "&nbsp;&nbsp;-&nbsp;&nbsp;" + pkt['raw']

            json_pretty = Prism.highlight(JSON.stringify(pkt, null, '\t'), Prism.languages.json, 'json');
            pkt_html = '<div class="title" id="' + title_id + '"><i class="dropdown icon"></i>' + from_to + '</div><div class="content"><p class="transition hidden"><pre class="language-json">' + json_pretty + '</p></p></div>'
            packetsdiv.prepend(pkt_html);
        }
    });

    $('.ui.accordion').accordion('refresh');

    // Update the count of messages shown
    cnt = size_dict(packet_list);
    //console.log("packets list " + cnt)
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
                    update_watchlist(data);
                    update_seenlist(data);
                    update_plugins(data);
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
