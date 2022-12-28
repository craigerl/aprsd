var cleared = false;

function size_dict(d){c=0; for (i in d) ++c; return c}

function init_messages() {
   const socket = io("/sendmsg");
   socket.on('connect', function () {
       console.log("Connected to socketio");
   });
   socket.on('connected', function(msg) {
       console.log("Connected!");
       console.log(msg);
   });

   socket.on("sent", function(msg) {
       if (cleared == false) {
           var msgsdiv = $("#msgsDiv");
           msgsdiv.html('')
           cleared = true
       }
       add_msg(msg);
   });

   socket.on("ack", function(msg) {
       update_msg(msg);
   });
   socket.on("reply", function(msg) {
       update_msg(msg);
   });

}

function add_msg(msg) {
    var msgsdiv = $("#sendMsgsDiv");

    ts_str = msg["ts"].toString();
    ts = ts_str.split(".")[0]*1000;
    var d = new Date(ts).toLocaleDateString("en-US")
    var t = new Date(ts).toLocaleTimeString("en-US")

    from = msg['from']
    title_id = 'title_tx'
    var from_to = d + " " + t + "&nbsp;&nbsp;&nbsp;&nbsp;" + from + " > "

    if (msg.hasOwnProperty('to')) {
        from_to = from_to + msg['to']
    }
    from_to = from_to + "&nbsp;&nbsp;-&nbsp;&nbsp;" + msg['message']

    id = ts_str.split('.')[0]
    pretty_id = "pretty_" + id
    loader_id = "loader_" + id
    ack_id = "ack_" + id
    reply_id = "reply_" + id
    span_id = "span_" + id
    json_pretty = Prism.highlight(JSON.stringify(msg, null, '\t'), Prism.languages.json, 'json');
    msg_html = '<div class="ui title" id="' + title_id + '"><i class="dropdown icon"></i>';
    msg_html += '<div class="ui active inline loader" id="' + loader_id  +'" data-content="Waiting for Ack"></div>&nbsp;';
    msg_html += '<i class="thumbs down outline icon" id="' + ack_id + '" data-content="Waiting for ACK"></i>&nbsp;';
    msg_html += '<i class="thumbs down outline icon" id="' + reply_id + '" data-content="Waiting for Reply"></i>&nbsp;';
    msg_html += '<span id="' + span_id + '">' + from_to +'</span></div>';
    msg_html += '<div class="content"><p class="transition hidden"><pre id="' + pretty_id + '" class="language-json">' + json_pretty + '</p></p></div>'
    msgsdiv.prepend(msg_html);
    $('.ui.accordion').accordion('refresh');
}

function update_msg(msg) {
   var msgsdiv = $("#sendMsgsDiv");
    // We have an existing entry
    ts_str = msg["ts"].toString();
    id = ts_str.split('.')[0]
    pretty_id = "pretty_" + id
    loader_id = "loader_" + id
    reply_id = "reply_" + id
    ack_id = "ack_" + id
    span_id = "span_" + id



    if (msg['ack'] == true) {
        var loader_div = $('#' + loader_id);
        var ack_div = $('#' + ack_id);
        loader_div.removeClass('ui active inline loader');
        loader_div.addClass('ui disabled loader');
        ack_div.removeClass('thumbs up outline icon');
        ack_div.addClass('thumbs up outline icon');
    }

    if (msg['reply'] !== null) {
        var reply_div = $('#' + reply_id);
        reply_div.removeClass("thumbs down outline icon");
        reply_div.addClass('reply icon');
        reply_div.attr('data-content', 'Got Reply');

        var d = new Date(ts).toLocaleDateString("en-US")
        var t = new Date(ts).toLocaleTimeString("en-US")
        var from_to = d + " " + t + "&nbsp;&nbsp;&nbsp;&nbsp;" + from + " > "

        if (msg.hasOwnProperty('to')) {
            from_to = from_to + msg['to']
        }
        from_to = from_to + "&nbsp;&nbsp;-&nbsp;&nbsp;" + msg['message']
        from_to += "&nbsp;&nbsp; ===> " + msg["reply"]["message_text"]

        var span_div = $('#' + span_id);
        span_div.html(from_to);
    }

    var pretty_pre = $("#" + pretty_id);
    pretty_pre.html('');
    json_pretty = Prism.highlight(JSON.stringify(msg, null, '\t'), Prism.languages.json, 'json');
    pretty_pre.html(json_pretty);
    $('.ui.accordion').accordion('refresh');
}
