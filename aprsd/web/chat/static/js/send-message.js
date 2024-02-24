var cleared = false;
var callsign_list = {};
var callsign_location = {};
var message_list = {};
var from_msg_list = {};
var selected_tab_callsign = null;
const socket = io("/sendmsg");

MSG_TYPE_TX = "tx";
MSG_TYPE_RX = "rx";
MSG_TYPE_ACK = "ack";

function reload_popovers() {
    $('[data-bs-toggle="popover"]').popover(
        {html: true, animation: true}
    );
}

function build_location_string(msg) {
   dt = new Date(parseInt(msg['lasttime']) * 1000);
   loc = "Last Location Update: " + dt.toLocaleString();
   loc += "<br>Latitude: " + msg['lat'] + "<br>Longitude: " + msg['lon'];
   loc += "<br>" + "Altitude: " + msg['altitude'] + " m";
   loc += "<br>" + "Speed: " + msg['speed'] + " kph";
   loc += "<br>" + "Bearing: " + msg['course'] + "°";
   loc += "<br>" + "distance: " + msg['distance'] + " km";
   return loc;
}

function build_location_string_small(msg) {

   dt = new Date(parseInt(msg['lasttime']) * 1000);

    loc = "" + msg['distance'] + "km";
    //loc += "Lat " + msg['lat'] + "&nbsp;Lon " + msg['lon'];
    loc += "@" + msg['course'] + "°";
    //loc += "&nbsp;Distance " + msg['distance'] + " km";
    loc += "&nbsp;" + dt.toLocaleString();
    return loc;
}

function size_dict(d){c=0; for (i in d) ++c; return c}

function raise_error(msg) {
   $.toast({
       heading: 'Error',
       text: msg,
       loader: true,
       loaderBg: '#9EC600',
       position: 'top-center',
   });
}

function init_chat() {
   socket.on('connect', function () {
       console.log("Connected to socketio");
   });
   socket.on('connected', function(msg) {
       console.log("Connected!");
       console.log(msg);
   });

   socket.on("sent", function(msg) {
       if (cleared === false) {
           var msgsdiv = $("#msgsTabsDiv");
           msgsdiv.html('');
           cleared = true;
       }
       msg["type"] = MSG_TYPE_TX;
       sent_msg(msg);
   });

   socket.on("ack", function(msg) {
       msg["type"] = MSG_TYPE_ACK;
       ack_msg(msg);
   });

   socket.on("new", function(msg) {
       if (cleared === false) {
           var msgsdiv = $("#msgsTabsDiv");
           msgsdiv.html('')
           cleared = true;
       }
       msg["type"] = MSG_TYPE_RX;
       from_msg(msg);
   });

   socket.on("callsign_location", function(msg) {
       console.log("CALLSIGN Location!");
       console.log(msg);
       now = new Date();
       msg['last_updated'] = now;
       callsign_location[msg['callsign']] = msg;

       location_id = callsign_location_content(msg['callsign'], true);
       location_string = build_location_string_small(msg);
       $(location_id).html(location_string);
       $(location_id+"Spinner").addClass('d-none');
       save_data();
   });

   $("#sendform").submit(function(event) {
       event.preventDefault();
       to_call = $('#to_call').val();
       message = $('#message').val();
       path = $('#pkt_path option:selected').val();
       if (to_call == "") {
           raise_error("You must enter a callsign to send a message")
           return false;
       } else {
           if (message == "") {
               raise_error("You must enter a message to send")
               return false;
           }
           msg = {'to': to_call, 'message': message, 'path': path};
           //console.log(msg);
           socket.emit("send", msg);
           $('#message').val('');
       }
   });

   init_gps();
   // Try and load any existing chat threads from last time
   init_messages();
}


function tab_string(callsign, id=false) {
    name = "msgs"+callsign;
    if (id) {
        return "#"+name;
    } else {
        return name;
    }
}

function tab_li_string(callsign, id=false) {
    //The id of the LI containing the tab
    return tab_string(callsign,id)+"Li";
}

function tab_notification_id(callsign, id=false) {
    // The ID of the span that contains the notification count
    return tab_string(callsign, id)+"notify";
}

function tab_content_name(callsign, id=false) {
   return tab_string(callsign, id)+"Content";
}

function tab_content_speech_wrapper(callsign, id=false) {
    return tab_string(callsign, id)+"SpeechWrapper";
}

function tab_content_speech_wrapper_id(callsign) {
    return "#"+tab_content_speech_wrapper(callsign);
}

function content_divname(callsign) {
    return "#"+tab_content_name(callsign);
}

function callsign_tab(callsign) {
    return "#"+tab_string(callsign);
}

function callsign_location_popover(callsign, id=false) {
    return tab_string(callsign, id)+"Location";
}

function callsign_location_content(callsign, id=false) {
    return tab_string(callsign, id)+"LocationContent";
}

function bubble_msg_id(msg, id=false) {
    // The id of the div that contains a specific message
    name = msg["from_call"] + "_" + msg["msgNo"];
    if (id) {
        return "#"+name;
    } else {
        return name;
    }
}

function message_ts_id(msg) {
    //Create a 'id' from the message timestamp
    ts_str = msg["timestamp"].toString();
    ts = ts_str.split(".")[0]*1000;
    id = ts_str.split('.')[0];
    return {'timestamp': ts, 'id': id};
}

function time_ack_from_msg(msg)  {
    // Return the time and ack_id from a message
    ts_id = message_ts_id(msg);
    ts = ts_id['timestamp'];
    id = ts_id['id'];
    ack_id = "ack_" + id

    var d = new Date(ts).toLocaleDateString("en-US")
    var t = new Date(ts).toLocaleTimeString("en-US")
    return {'time': t, 'date': d, 'ack_id': ack_id};
}

function save_data() {
  // Save the relevant data to local storage
  localStorage.setItem('callsign_list', JSON.stringify(callsign_list));
  localStorage.setItem('message_list', JSON.stringify(message_list));
  localStorage.setItem('callsign_location', JSON.stringify(callsign_location));
}

function init_messages() {
    // This tries to load any previous conversations from local storage
    callsign_list = JSON.parse(localStorage.getItem('callsign_list'));
    message_list = JSON.parse(localStorage.getItem('message_list'));
    callsign_location = JSON.parse(localStorage.getItem('callsign_location'));
    if (callsign_list == null) {
       callsign_list = {};
    }
    if (message_list == null) {
       message_list = {};
    }
    if (callsign_location == null) {
       callsign_location = {};
    }
    console.log(callsign_list);
    console.log(message_list);
    console.log(callsign_location);

    // Now loop through each callsign and add the tabs
    first_callsign = null;
    for (callsign in callsign_list) {
        if (first_callsign === null) {
            first_callsign = callsign;
            active = true;
        } else {
            active = false;
        }
        create_callsign_tab(callsign, active);
    }
    // and then populate the messages in order
    for (callsign in message_list) {
        new_callsign = true;
        cleared = true;
        for (id in message_list[callsign]) {
            msg = message_list[callsign][id];
            info = time_ack_from_msg(msg);
            t = info['time'];
            d = info['date'];
            ack_id = false;
            acked = false;
            if (msg['type'] == MSG_TYPE_TX) {
                ack_id = info['ack_id'];
                acked = msg['ack'];
            }
            msg_html = create_message_html(d, t, msg['from_call'], msg['to_call'],
                                           msg['message_text'], ack_id, msg, acked);
            append_message_html(callsign, msg_html, new_callsign);
            new_callsign = false;
        }
    }

    if (first_callsign !== null) {
      callsign_select(first_callsign);
    }
}

function scroll_main_content(callsign=false) {
   var wc = $('#wc-content');
   var d = $('#msgsTabContent');
   var scrollHeight = wc.prop('scrollHeight');
   var clientHeight = wc.prop('clientHeight');

   if (callsign) {
       div_id = content_divname(callsign);
       c_div = $(content_divname(callsign));
       //console.log("c_div("+div_id+") " + c_div);
       c_height = c_div.height();
       c_scroll_height = c_div.prop('scrollHeight');
       //console.log("callsign height " + c_height + " scrollHeight " + c_scroll_height);
       if (c_height === undefined) {
           return false;
       }
       if (c_height > clientHeight) {
           wc.animate({ scrollTop: c_scroll_height }, 500);
       } else {
           wc.animate({ scrollTop: 0 }, 500);
       }
   } else {
       if (scrollHeight > clientHeight) {
           wc.animate({ scrollTop: wc.prop('scrollHeight') }, 500);
       } else {
           wc.animate({ scrollTop: 0 }, 500);
       }
   }
}

function create_callsign_tab(callsign, active=false) {
  //Create the html for the callsign tab and insert it into the DOM
  var callsignTabs = $("#msgsTabList");
  tab_id = tab_string(callsign);
  tab_id_li = tab_li_string(callsign);
  tab_notify_id = tab_notification_id(callsign);
  tab_content = tab_content_name(callsign);
  popover_id = callsign_location_popover(callsign);
  if (active) {
    active_str = "active";
  } else {
    active_str = "";
  }

  item_html = '<li class="nav-item" role="presentation" callsign="'+callsign+'" id="'+tab_id_li+'">';
  //item_html += '<button onClick="callsign_select(\''+callsign+'\');" callsign="'+callsign+'" class="nav-link '+active_str+'" id="'+tab_id+'" data-bs-toggle="tab" data-bs-target="#'+tab_content+'" type="button" role="tab" aria-controls="'+callsign+'" aria-selected="true">';
  item_html += '<button onClick="callsign_select(\''+callsign+'\');" callsign="'+callsign+'" class="nav-link position-relative '+active_str+'" id="'+tab_id+'" data-bs-toggle="tab" data-bs-target="#'+tab_content+'" type="button" role="tab" aria-controls="'+callsign+'" aria-selected="true">';
  item_html += callsign+'&nbsp;&nbsp;';
  item_html += '<span onclick="delete_tab(\''+callsign+'\');">×</span>';
  item_html += '</button></li>'

  callsignTabs.append(item_html);
  create_callsign_tab_content(callsign, active);
}

function create_callsign_tab_content(callsign, active=false) {
  var callsignTabsContent = $("#msgsTabContent");
  tab_id = tab_string(callsign);
  tab_content = tab_content_name(callsign);
  wrapper_id = tab_content_speech_wrapper(callsign);
  if (active) {
    active_str = "show active";
  } else {
    active_str = '';
  }

  location_str = "Unknown Location"
  if (callsign in callsign_location) {
    location_str = build_location_string_small(callsign_location[callsign]);
    location_class = '';
  }

  location_id = callsign_location_content(callsign);

  item_html = '<div class="tab-pane fade '+active_str+'" id="'+tab_content+'" role="tabpanel" aria-labelledby="'+tab_id+'">';
  item_html += '<div class="" style="border: 1px solid #999999;background-color:#aaaaaa;">';
  item_html += '<div class="row" style="padding-top:4px;padding-bottom:4px;background-color:#aaaaaa;margin:0px;">';
  item_html +=   '<div class="d-flex col-md-10 justify-content-left" style="padding:0px;margin:0px;">';
  item_html +=     '<button onclick="call_callsign_location(\''+callsign+'\');" style="margin-left:2px;padding: 0px 4px 0px 4px;" type="button" class="btn btn-primary">';
  item_html +=     '<span id="'+location_id+'Spinner" class="d-none spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>Update</button>';
  item_html +=   '&nbsp;<span id="'+location_id+'">'+location_str+'</span></div>';
  item_html += '</div>';
  item_html += '<div class="speech-wrapper" id="'+wrapper_id+'"></div>';
  item_html += '</div>';
  callsignTabsContent.append(item_html);
}

function delete_tab(callsign) {
    // User asked to delete the tab and the conversation
    tab_id = tab_string(callsign, true);
    tab_id_li = tab_li_string(callsign, true);
    tab_content = tab_content_name(callsign, true);
    $(tab_id_li).remove();
    $(tab_content).remove();
    delete callsign_list[callsign];
    delete message_list[callsign];
    delete callsign_location[callsign];

    // Now select the first tab
    first_tab = $("#msgsTabList").children().first().children().first();
    console.log(first_tab);
    $(first_tab).click();
    save_data();
}

function add_callsign(callsign, msg) {
   /* Ensure a callsign exists in the left hand nav */
  if (callsign in callsign_list) {
      return false
  }
  len = Object.keys(callsign_list).length;
  if (len == 0) {
      active = true;
  } else {
      active = false;
  }
  create_callsign_tab(callsign, active);
  callsign_list[callsign] = '';
  return true;
}

function update_callsign_path(callsign, msg) {
  //Get the selected path to save for this callsign
  path = msg['path']
  $('#pkt_path').val(path);
  callsign_list[callsign] = path;

}

function append_message(callsign, msg, msg_html) {
  new_callsign = false
  if (!message_list.hasOwnProperty(callsign)) {
       message_list[callsign] = {};
  }
  ts_id = message_ts_id(msg);
  id = ts_id['id']
  message_list[callsign][id] = msg;
  if (selected_tab_callsign != callsign) {
      // We need to update the notification for the tab
      tab_notify_id = tab_notification_id(callsign, true);
      // get the current count of notifications
      count = parseInt($(tab_notify_id).text());
      count += 1;
      $(tab_notify_id).text(count);
      $(tab_notify_id).removeClass('visually-hidden');
  }

  // Find the right div to place the html

  new_callsign = add_callsign(callsign, msg);
  update_callsign_path(callsign, msg);
  append_message_html(callsign, msg_html, new_callsign);
  len = Object.keys(callsign_list).length;
  if (new_callsign && len == 1) {
      //Now click the tab if and only if there is only one tab
      callsign_tab_id = callsign_tab(callsign);
      $(callsign_tab_id).click();
      callsign_select(callsign);
  }
}


function append_message_html(callsign, msg_html, new_callsign) {
  var msgsTabs = $('#msgsTabsDiv');
  divname_str = tab_content_name(callsign);
  divname = content_divname(callsign);
  tab_content = tab_content_name(callsign);
  wrapper_id = tab_content_speech_wrapper_id(callsign);

  $(wrapper_id).append(msg_html);

  if ($(wrapper_id).children().length > 0) {
      $(wrapper_id).animate({scrollTop: $(wrapper_id)[0].scrollHeight}, "fast");
  }
}

function create_message_html(date, time, from, to, message, ack_id, msg, acked=false) {
    div_id = from + "_" + msg.msgNo;
    if (ack_id) {
      alt = " alt"
    } else {
      alt = ""
    }

    bubble_class = "bubble" + alt + " text-nowrap"
    bubble_name_class = "bubble-name" + alt
    bubble_msgid = bubble_msg_id(msg);
    date_str = date + " " + time;
    sane_date_str = date_str.replace(/ /g,"").replaceAll("/","").replaceAll(":","");

    bubble_msg_class = "bubble-message";
    if (ack_id) {
      bubble_arrow_class = "bubble-arrow alt";
      popover_placement = "left";
    } else {
      bubble_arrow_class = "bubble-arrow";
      popover_placement = "right";
    }

    msg_html = '<div class="bubble-row'+alt+'">';
    msg_html += '<div id="'+bubble_msgid+'" class="'+ bubble_class + '" ';
    msg_html +=  'title="APRS Raw Packet" data-bs-placement="'+popover_placement+'" data-bs-toggle="popover" ';
    msg_html +=  'data-bs-trigger="hover" data-bs-content="'+msg['raw']+'">';
    msg_html += '<div class="bubble-text">';
    msg_html += '<p class="'+ bubble_name_class +'">'+from+'&nbsp;&nbsp;';
    msg_html += '<span class="bubble-timestamp">'+date_str+'</span>';

    if (ack_id) {
        if (acked) {
            msg_html += '<span class="material-symbols-rounded md-10" id="' + ack_id + '">thumb_up</span>';
        } else {
            msg_html += '<span class="material-symbols-rounded md-10" id="' + ack_id + '">thumb_down</span>';
        }
    }
    msg_html += "</p>";
    msg_html += '<p class="' +bubble_msg_class+ '">'+message+'</p>';
    msg_html += '<div class="'+ bubble_arrow_class + '"></div>';
    msg_html += "</div></div></div>";

    return msg_html
}

function flash_message(msg) {
    // Callback function to bring a hidden box back
    msg_id = bubble_msg_id(msg, true);
    $(msg_id).fadeOut(100).fadeIn(100).fadeOut(100).fadeIn(100).fadeOut(100).fadeIn(100);
}

function sent_msg(msg) {
    info = time_ack_from_msg(msg);
    t = info['time'];
    d = info['date'];
    ack_id = info['ack_id'];

    msg_html = create_message_html(d, t, msg['from_call'], msg['to_call'], msg['message_text'], ack_id, msg, false);
    append_message(msg['to_call'], msg, msg_html);
    save_data();
    scroll_main_content(msg['from_call']);
}

function from_msg(msg) {
   if (!from_msg_list.hasOwnProperty(msg["from_call"])) {
        from_msg_list[msg["from_call"]] = new Array();
   }

   if (msg["msgNo"] in from_msg_list[msg["from_call"]]) {
       // We already have this message
       //console.log("We already have this message msgNo=" + msg["msgNo"]);
       // Do some flashy thing?
       flash_message(msg);
       return false
   } else {
       from_msg_list[msg["from_call"]][msg["msgNo"]] = msg
   }
   info = time_ack_from_msg(msg);
   t = info['time'];
   d = info['date'];
   ack_id = info['ack_id'];

   from = msg['from_call']
   msg_html = create_message_html(d, t, from, false, msg['message_text'], false, msg, false);
   append_message(from, msg, msg_html);
   save_data();
   scroll_main_content(from);
}

function ack_msg(msg) {
   // Acknowledge a message
   // We have an existing entry
   ts_id = message_ts_id(msg);
   id = ts_id['id'];
   //Mark the message as acked
   callsign = msg['to_call'];
   // Ensure the message_list has this callsign
   if (!message_list.hasOwnProperty(callsign)) {
       return false
   }
   // Ensure the message_list has this id
   if (!message_list[callsign].hasOwnProperty(id)) {
       return false
   }
   if (message_list[callsign][id]['ack'] == true) {
       return false;
   }
   message_list[callsign][id]['ack'] = true;
   ack_id = "ack_" + id

   if (msg['ack'] == true) {
       var ack_div = $('#' + ack_id);
       ack_div.html('thumb_up');
   }

   //$('.ui.accordion').accordion('refresh');
   save_data();
   scroll_main_content();
}

function callsign_select(callsign) {
    var tocall = $("#to_call");
    tocall.val(callsign);
    scroll_main_content(callsign);
    selected_tab_callsign = callsign;
    tab_notify_id = tab_notification_id(callsign, true);
    $(tab_notify_id).addClass('visually-hidden');
    $(tab_notify_id).text(0);
    // Now update the path
    $('#pkt_path').val(callsign_list[callsign]);
}

function call_callsign_location(callsign) {
    msg = {'callsign': callsign};
    socket.emit("get_callsign_location", msg);
    location_id = callsign_location_content(callsign, true)+"Spinner";
    $(location_id).removeClass('d-none');
}
