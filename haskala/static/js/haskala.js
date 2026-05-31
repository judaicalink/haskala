document.addEventListener('DOMContentLoaded', function () {
    initMap();
    initPlacesMap();
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
// Multi-marker map for the places index
// ------------------
function initPlacesMap() {
    var el = document.getElementById('places-map');
    if (!el) return;

    var raw = el.dataset.markers;
    if (!raw) return;

    var markers;
    try {
        markers = JSON.parse(raw);
    } catch (e) {
        return;
    }
    if (!Array.isArray(markers) || markers.length === 0) return;

    var map = L.map('places-map');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    var group = L.featureGroup();
    markers.forEach(function (m) {
        if (m.lat == null || m.lng == null) return;
        var popup = m.url
            ? '<a href="' + m.url + '">' + m.name + '</a>'
            : m.name;
        L.marker([m.lat, m.lng]).bindPopup(popup).addTo(group);
    });
    group.addTo(map);

    var bounds = group.getBounds();
    if (bounds.isValid()) {
        map.fitBounds(bounds, {padding: [20, 20], maxZoom: 8});
    } else {
        map.setView([50, 10], 4);
    }
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
