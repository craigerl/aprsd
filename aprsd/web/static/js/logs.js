function init_logs() {
   const socket = io("/logs");
   socket.on('connect', function () {
       console.log("Connected to logs socketio");
   });

   socket.on('connected', function(msg) {
       console.log("Connected to /logs");
       console.log(msg);
   });

   socket.on('log_entry', function(data) {
        update_logs(data);
   });

};


function update_logs(data) {
    var code_block = $('#logtext')
    entry = data["message"]
    const html_pretty = Prism.highlight(entry, Prism.languages.log, 'log');
    code_block.append(html_pretty + "<br>");
    var div = document.getElementById('logContainer');
    div.scrollTop = div.scrollHeight;
}
