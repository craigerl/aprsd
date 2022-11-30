var cleared = false;
var callsign_list = {};
var message_list = {};

function size_dict(d){c=0; for (i in d) ++c; return c}

function init_chat() {
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
           var msgsdiv = $("#msgsTabsDiv");
           msgsdiv.html('')
           cleared = true
       }
       sent_msg(msg);
   });

   socket.on("ack", function(msg) {
       update_msg(msg);
   });

   socket.on("new", function(msg) {
       if (cleared == false) {
           var msgsdiv = $("#msgsTabsDiv");
           msgsdiv.html('')
           cleared = true
       }
       from_msg(msg);
   });

   $("#sendform").submit(function(event) {
       event.preventDefault();
       msg = {'to': $('#to_call').val().toUpperCase(),
              'message': $('#message').val(),
              }
       socket.emit("send", msg);
       $('#message').val('');
       $('#to_call').val('');
   });

   init_gps();
}


function add_callsign(callsign) {
   /* Ensure a callsign exists in the left hand nav */
   dropdown = $('#callsign_dropdown')

  if (callsign in callsign_list) {
      console.log(callsign+' already in list.')
      return false
  }

  var callsignTabs = $("#callsignTabs");
  tab_name = tab_string(callsign);
  tab_content = tab_content_name(callsign);
  divname = content_divname(callsign);

  item_html = '<div class="active item" id="'+tab_name+'" onclick="openCallsign(event, \''+callsign+'\');">'+callsign+'</div>';
  callsignTabs.append(item_html);

  callsign_list[callsign] = {'name': callsign, 'value': callsign, 'text': callsign}
  return true
}

function append_message(callsign, msg, msg_html) {
  console.log('append_message');
  new_callsign = false
  if (!message_list.hasOwnProperty(callsign)) {
       message_list[callsign] = new Array();
  }
  message_list[callsign].push(msg);

  // Find the right div to place the html
  new_callsign = add_callsign(callsign);
  append_message_html(callsign, msg_html, new_callsign);
  if (new_callsign) {
      //click on the new tab
      click_div = '#'+tab_string(callsign);
      console.log("Click on "+click_div);
      $(click_div).click();
  }
}

function tab_string(callsign) {
  return "msgs"+callsign;
}

function tab_content_name(callsign) {
   return tab_string(callsign)+"Content";
}

function content_divname(callsign) {
    return "#"+tab_content_name(callsign);
}

function append_message_html(callsign, msg_html, new_callsign) {
  var msgsTabs = $('#msgsTabsDiv');
  divname_str = tab_content_name(callsign);
  divname = content_divname(callsign);
  if (new_callsign) {
      // we have to add a new DIV
      msg_div_html = '<div class="tabcontent" id="'+divname_str+'" style="height:450px;">'+msg_html+'</div>';
      msgsTabs.append(msg_div_html);
  } else {
      var msgDiv = $(divname);
      msgDiv.append(msg_html);
  }

  $(divname).animate({scrollTop: $(divname)[0].scrollHeight}, "slow");
}

function create_message_html(time, from, to, message, ack) {
    msg_html = '<div class="item">';
    msg_html += '<div class="tiny text">'+time+'</div>';
    msg_html += '<div class="middle aligned content">';
    msg_html += '<div class="tiny red header">'+from+'</div>';
    if (ack) {
        msg_html += '<i class="thumbs down outline icon" id="' + ack_id + '" data-content="Waiting for ACK"></i>';
    } else {
        msg_html += '<i class="phone volume icon" data-content="Recieved Message"></i>';
    }
    msg_html += '<div class="middle aligned content">>&nbsp;&nbsp;&nbsp;</div>';
    msg_html += '</div>';
    msg_html += '<div class="middle aligned content">'+message+'</div>';
    msg_html += '</div><br>';

    return msg_html
}

function sent_msg(msg) {
    var msgsdiv = $("#sendMsgsDiv");

    ts_str = msg["ts"].toString();
    ts = ts_str.split(".")[0]*1000;
    id = ts_str.split('.')[0]
    ack_id = "ack_" + id

    var d = new Date(ts).toLocaleDateString("en-US")
    var t = new Date(ts).toLocaleTimeString("en-US")

    msg_html = create_message_html(t, msg['from'], msg['to'], msg['message'], ack_id);
    append_message(msg['to'], msg, msg_html);
}

function from_msg(msg) {
   var msgsdiv = $("#sendMsgsDiv");

   // We have an existing entry
   ts_str = msg["ts"].toString();
   ts = ts_str.split(".")[0]*1000;
   id = ts_str.split('.')[0]
   ack_id = "ack_" + id

   var d = new Date(ts).toLocaleDateString("en-US")
   var t = new Date(ts).toLocaleTimeString("en-US")

   from = msg['from']
   msg_html = create_message_html(t, from, false, msg['message'], false);
   append_message(from, msg, msg_html);
}

function update_msg(msg) {
   var msgsdiv = $("#sendMsgsDiv");
    // We have an existing entry
    ts_str = msg["ts"].toString();
    id = ts_str.split('.')[0]
    pretty_id = "pretty_" + id
    loader_id = "loader_" + id
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

    $('.ui.accordion').accordion('refresh');
}

function callsign_select(callsign) {
   var tocall = $("#to_call");
   tocall.val(callsign);
}

function reset_Tabs() {
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
}

function openCallsign(evt, callsign) {
  var i, tabcontent, tablinks;

  tab_content = tab_content_name(callsign);

  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(tab_content).style.display = "block";
  evt.target.className += " active";
  callsign_select(callsign);
}
