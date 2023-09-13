
function init_gps() {
   console.log("init_gps Called.")
   console.log("latitude: "+latitude)
   console.log("longitude: "+longitude)
   $("#send_beacon").click(function() {
       console.log("Send a beacon!")
       if (!isNaN(latitude) && !isNaN(longitude)) {
           // webchat admin has hard coded lat/long in the config file
           showPosition({'coords': {'latitude': latitude, 'longitude': longitude}})
       } else {
           // Try to get the current location from the browser
           getLocation();
       }
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
      heading: 'Sending GPS Beacon',
      text: "Latitude: "+position.coords.latitude+"<br>Longitude: "+position.coords.longitude,
      loader: true,
      loaderBg: '#9EC600',
      position: 'top-center',
  });

  console.log("Sending GPS msg")
  socket.emit("gps", msg);
}
