// script.js

document.addEventListener('DOMContentLoaded', function() {
    const spinButton = document.getElementById('spin-button');
    const wheel = document.getElementById('wheel');
    const result = document.getElementById('result');

    spinButton.addEventListener('click', function() {
        // Generate a random rotation angle with at least two full spins (720 degrees)
        const rotation = Math.floor(Math.random() * 360) + 720;
        wheel.style.transition = "transform 3s ease-out";
        wheel.style.transform = "rotate(" + rotation + "deg)";

        // After the spin animation (3 seconds), call the backend to get the chore
        setTimeout(function() {
            fetch('/spin', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        result.innerText = data.error;
                    } else {
                        result.innerText = "Your chore: " + data.chore + " (" + data.type + ")";
                    }
                });
        }, 3000);
    });
});
