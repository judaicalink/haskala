document.addEventListener('DOMContentLoaded', function () {
    initMap();
    initScrollTopButton();
});

// ------------------
// Karte (Leaflet)
// ------------------
function initMap() {
    var mapEl = document.getElementById('map');
    if (!mapEl) return;

    var lat = parseFloat(mapEl.dataset.lat);
    var lng = parseFloat(mapEl.dataset.lng);
    var name = mapEl.dataset.name || '';

    if (isNaN(lat) || isNaN(lng)) return;

    var map = L.map('map').setView([lat, lng], 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    L.marker([lat, lng]).addTo(map).bindPopup(name);
}

// ------------------
// Scroll-to-top Button
// ------------------
function initScrollTopButton() {
    var btn = document.getElementById('scrollTopBtn');
    if (!btn) return;

    // beim Klick nach oben scrollen
    btn.addEventListener('click', function () {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });

    // Ein-/Ausblenden beim Scrollen
    window.addEventListener('scroll', function () {
        if (window.scrollY > 200) {
            btn.classList.add('show');
        } else {
            btn.classList.remove('show');
        }
    });
}
