var cleared = false;
var callsign_list = {};
var message_list = {};
var from_msg_list = {};
const socket = io("/sendmsg");

MSG_TYPE_TX = "tx";
MSG_TYPE_RX = "rx";
MSG_TYPE_ACK = "ack";

function size_dict(d){c=0; for (i in d) ++c; return c}

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
           console.log("CLEARING #msgsTabsDiv");
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

   $("#sendform").submit(function(event) {
       event.preventDefault();
       msg = {'to': $('#to_call').val(),
              'message': $('#message').val(),
              }
       socket.emit("send", msg);
       $('#message').val('');
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

function message_ts_id(msg) {
    //Create a 'id' from the message timestamp
    ts_str = msg["ts"].toString();
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
}

function init_messages() {
    // This tries to load any previous conversations from local storage
    callsign_list = JSON.parse(localStorage.getItem('callsign_list'));
    message_list = JSON.parse(localStorage.getItem('message_list'));
    if (callsign_list == null) {
       callsign_list = {};
    }
    if (message_list == null) {
       message_list = {};
    }
    console.log(callsign_list);
    console.log(message_list);

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
            msg_html = create_message_html(d, t, msg['from'], msg['to'], msg['message'], ack_id, msg, acked);
            append_message_html(callsign, msg_html, new_callsign);
            new_callsign = false;
        }
    }
}

function create_callsign_tab(callsign, active=false) {
  //Create the html for the callsign tab and insert it into the DOM
  var callsignTabs = $("#msgsTabList");
  tab_id = tab_string(callsign);
  tab_id_li = tab_li_string(callsign);
  tab_content = tab_content_name(callsign);
  if (active) {
    active_str = "active";
  } else {
    active_str = "";
  }

  item_html = '<li class="nav-item" role="presentation" callsign="'+callsign+'" id="'+tab_id_li+'">';
  item_html += '<button onClick="callsign_select(\''+callsign+'\');" callsign="'+callsign+'" class="nav-link '+active_str+'" id="'+tab_id+'" data-bs-toggle="tab" data-bs-target="#'+tab_content+'" type="button" role="tab" aria-controls="'+callsign+'" aria-selected="true">';
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

  item_html = '<div class="tab-pane fade '+active_str+'" id="'+tab_content+'" role="tabpanel" aria-labelledby="'+tab_id+'">';
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

    // Now select the first tab
    first_tab = $("#msgsTabList").children().first().children().first();
    console.log(first_tab);
    $(first_tab).click();
    save_data();
}

function add_callsign(callsign) {
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
  callsign_list[callsign] = true;
  return true
}

function append_message(callsign, msg, msg_html) {
  new_callsign = false
  if (!message_list.hasOwnProperty(callsign)) {
       //message_list[callsign] = new Array();
       message_list[callsign] = {};
  }
  ts_id = message_ts_id(msg);
  id = ts_id['id']
  message_list[callsign][id] = msg;

  // Find the right div to place the html
  new_callsign = add_callsign(callsign);
  append_message_html(callsign, msg_html, new_callsign);
  if (new_callsign) {
      //Now click the tab
      callsign_tab_id = callsign_tab(callsign);
      $(callsign_tab_id).click();
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
    div_id = from + "_" + msg.id;
    if (ack_id) {
      alt = " alt"
    } else {
      alt = ""
    }

    bubble_class = "bubble" + alt
    bubble_name_class = "bubble-name" + alt
    date_str = date + " " + time;

    msg_html = '<div class="bubble-row'+alt+'">';
    msg_html += '<div class="'+ bubble_class + '">';
    msg_html += '<div class="bubble-text">';
    msg_html += '<p class="'+ bubble_name_class +'">'+from+'&nbsp;&nbsp;';
    msg_html += '<span class="bubble-timestamp">'+date_str+'</span>';
    if (ack_id) {
        if (acked) {
            msg_html += '<span class="material-symbols-rounded" id="' + ack_id + '">thumb_up</span>';
        } else {
            msg_html += '<span class="material-symbols-rounded" id="' + ack_id + '">thumb_down</span>';
        }
    }
    msg_html += "</p>";
    bubble_msg_class = "bubble-message"
    if (ack_id) {
      bubble_arrow_class = "bubble-arrow alt"
    } else {
      bubble_arrow_class = "bubble-arrow"
    }

    msg_html += '<p class="' +bubble_msg_class+ '">'+message+'</p>';
    msg_html += '<div class="'+ bubble_arrow_class + '"></div>';
    msg_html += "</div></div></div>";

    return msg_html
}

function flash_message(msg) {
    // Callback function to bring a hidden box back
    id = msg.from + "_" + msg.id;
    var msgid = $('#'+id);
    msgid.effect("pulsate", { times:3 }, 2000);
}


function sent_msg(msg) {
    info = time_ack_from_msg(msg);
    t = info['time'];
    d = info['date'];
    ack_id = info['ack_id'];

    msg_html = create_message_html(d, t, msg['from'], msg['to'], msg['message'], ack_id, msg, false);
    append_message(msg['to'], msg, msg_html);
    save_data();
}

function from_msg(msg) {
   if (!from_msg_list.hasOwnProperty(msg.from)) {
        from_msg_list[msg.from] = new Array();
   }

   if (msg.id in from_msg_list[msg.from]) {
       // We already have this message
       console.log("We already have this message " + msg);
       // Do some flashy thing?
       flash_message(msg);
       return false
   } else {
       console.log("Adding message " + msg.id + " to " + msg.from);
       from_msg_list[msg.from][msg.id] = msg
   }

   info = time_ack_from_msg(msg);
   t = info['time'];
   d = info['date'];
   ack_id = info['ack_id'];

   from = msg['from']
   msg_html = create_message_html(d, t, from, false, msg['message'], false, msg, false);
   append_message(from, msg, msg_html);
   save_data();
}

function ack_msg(msg) {
   // Acknowledge a message
   console.log("ack_msg ");

   // We have an existing entry
   ts_id = message_ts_id(msg);
   console.log(ts_id)
   id = ts_id['id'];
   //Mark the message as acked
   callsign = msg['to'];
   // Ensure the message_list has this callsign
   if (!message_list.hasOwnProperty(callsign)) {
       console.log("No message_list for " + callsign);
       return false
   }
   // Ensure the message_list has this id
   if (!message_list[callsign].hasOwnProperty(id)) {
       console.log("No message_list for " + callsign + " " + id);
       return false
   }
   console.log("Marking message as acked " + callsign + " " + id)
   if (message_list[callsign][id]['ack'] == true) {
       console.log("Message already acked");
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
}

function callsign_select(callsign) {
   var tocall = $("#to_call");
   tocall.val(callsign);
   var d = $('#wc-content');
   d.animate({ scrollTop: d.prop('scrollHeight') }, 500);
}
