
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
        navigator.geolocation.getCurrentPosition(showPosition, showError);
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
          msg = "The request to get user location timed out."
          break;
        case error.UNKNOWN_ERROR:
          msg = "An unknown error occurred."
          break;
      }
      console.log(msg);
      $.toast({
          title: 'GPS Error',
          message: msg,
          showProgress: 'bottom',
          classProgress: 'red'
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

  socket.emit("gps", msg);
}
