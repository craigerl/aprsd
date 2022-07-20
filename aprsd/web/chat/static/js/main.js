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

function update_stats( data ) {
    $("#version").text( data["stats"]["aprsd"]["version"] );
    $("#aprs_connection").html( data["aprs_connection"] );
    $("#uptime").text( "uptime: " + data["stats"]["aprsd"]["uptime"] );
    short_time = data["time"].split(/\s(.+)/)[1];
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
}
