
function init_gps() {
   console.log("init_gps Called.")
   $("#send_beacon").click(function() {
       console.log("Send a beacon!")
       getLocation();
   });
}

function getLocation() {
    if (navigator.geolocation) {
        console.log("getCurrentPosition");
        try {
            navigator.geolocation.getCurrentPosition(
            showPosition, showError,
            {timeout:3000});
        } catch(err) {
            console.log("Failed to getCurrentPosition");
            console.log(err);
        }
    } else {
        var msg = "Geolocation is not supported by this browser."
        console.log(msg);
        alert(msg)
    }
}

function showError(error) {
    console.log("showError");
    console.log(error);
    var msg = "";
      switch(error.code) {
        case error.PERMISSION_DENIED:
          msg = "User denied the request for Geolocation."
          break;
        case error.POSITION_UNAVAILABLE:
          msg = "Location information is unavailable."
          break;
        case error.TIMEOUT:
          msg = "The location fix timed out."
          break;
        case error.UNKNOWN_ERROR:
          msg = "An unknown error occurred."
          break;
      }
      console.log(msg);
      $.toast({
          title: 'GPS Error',
          class: 'warning',
          position: 'middle center',
          message: msg,
          showProgress: 'top',
          classProgress: 'blue',
      });
}

function showPosition(position) {
  console.log("showPosition Called");
  msg = {
      'latitude': position.coords.latitude,
      'longitude': position.coords.longitude
  }
  console.log(msg);
  $.toast({
      title: 'Sending GPS Beacon',
      message: "Latitude: "+position.coords.latitude+"<br>Longitude: "+position.coords.longitude,
      showProgress: 'bottom',
      classProgress: 'red'
  });

  console.log("Sending GPS msg")
  socket.emit("gps", msg);
}
