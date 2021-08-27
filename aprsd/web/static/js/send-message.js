msgs_list = {};

function size_dict(d){c=0; for (i in d) ++c; return c}

function update_messages(data) {
   msgs_cnt = size_dict(data);
   $('#msgs_count').html(msgs_cnt);

   var msgsdiv = $("#msgsDiv");
   //nuke the contents first, then add to it.
   if (size_dict(msgs_list) == 0 && size_dict(data) > 0) {
         msgsdiv.html('')
   }

   jQuery.each(data, function(i, val) {
        if ( msgs_list.hasOwnProperty(val["ts"]) == false ) {
            // Store the packet
            msgs_list[val["ts"]] = val;
            ts_str = val["ts"].toString();
            ts = ts_str.split(".")[0]*1000;
            var d = new Date(ts).toLocaleDateString("en-US")
            var t = new Date(ts).toLocaleTimeString("en-US")

            from = val['from']
            title_id = 'title_tx'
            var from_to = d + " " + t + "&nbsp;&nbsp;&nbsp;&nbsp;" + from + " > "

            if (val.hasOwnProperty('to')) {
                from_to = from_to + val['to']
            }
            from_to = from_to + "&nbsp;&nbsp;-&nbsp;&nbsp;" + val['raw']

            id = ts_str.split('.')[0]
            pretty_id = "pretty_" + id
            loader_id = "loader_" + id
            reply_id = "reply_" + id
            json_pretty = Prism.highlight(JSON.stringify(val, null, '\t'), Prism.languages.json, 'json');
            msg_html = '<div class="ui title" id="' + title_id + '"><i class="dropdown icon"></i>';
            msg_html += '<div class="ui active inline loader" id="' + loader_id  +'" data-content="Waiting for Ack"></div>&nbsp;';
            msg_html += '<i class="thumbs down outline icon" id="' + reply_id + '" data-content="Waiting for Reply"></i>&nbsp;' + from_to + '</div>';
            msg_html += '<div class="content"><p class="transition hidden"><pre id="' + pretty_id + '" class="language-json">' + json_pretty + '</p></p></div>'
            msgsdiv.prepend(msg_html);
        } else {
            // We have an existing entry
            msgs_list[val["ts"]] = val;
            ts_str = val["ts"].toString();
            id = ts_str.split('.')[0]
            pretty_id = "pretty_" + id
            loader_id = "loader_" + id
            reply_id = "reply_" + id
            var pretty_pre = $("#" + pretty_id);
            if (val['ack'] == true) {
                var loader_div = $('#' + loader_id);
                loader_div.removeClass('ui active inline loader');
                loader_div.addClass('ui disabled loader');
                loader_div.attr('data-content', 'Got reply');
            }

            if (val['reply'] !== null) {
                var reply_div = $('#' + reply_id);
                reply_div.removeClass("thumbs down outline icon");
                reply_div.addClass('thumbs up outline icon');
                reply_div.attr('data-content', 'Got Reply');
            }

            pretty_pre.html('');
            json_pretty = Prism.highlight(JSON.stringify(val, null, '\t'), Prism.languages.json, 'json');
            pretty_pre.html(json_pretty);
        }
    });

    $('.ui.accordion').accordion('refresh');

}
