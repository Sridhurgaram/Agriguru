function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                sendLocation(position.coords.latitude, position.coords.longitude);
            },
            function(error) {
                document.getElementById('result').innerText = "Error getting location: " + error.message;
            }
        );
    } else {
        document.getElementById('result').innerText = "Geolocation is not supported by this browser.";
    }
}

function sendManualLocation() {
    const input = document.getElementById('manualLocation').value;
    const parts = input.split(',');
    if (parts.length !== 2) {
        document.getElementById('result').innerText = "Please enter latitude and longitude separated by a comma.";
        return;
    }
    const latitude = parseFloat(parts[0].trim());
    const longitude = parseFloat(parts[1].trim());
    if (isNaN(latitude) || isNaN(longitude)) {
        document.getElementById('result').innerText = "Invalid coordinates.";
        return;
    }
    sendLocation(latitude, longitude);
}

function sendLocation(latitude, longitude) {
    document.getElementById('result').innerText = "Processing...";

    // Get today's date in YYYY-MM-DD format
    const today = new Date().toISOString().split('T')[0];

    // Optional: Replace 'Chennai' with a function if you want dynamic district detection
    const district = "Chennai";

    fetch('/get_recommendation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            latitude: latitude,
            longitude: longitude,
            district: district,
            date: today
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.result) {
            document.getElementById('result').innerText = data.result;
        } else if (data.error) {
            document.getElementById('result').innerText = "Error: " + data.error;
        }
    })
    .catch(err => {
        document.getElementById('result').innerText = "Error: " + err;
    });
}
