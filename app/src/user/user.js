import './user.css';

export function renderUserView(container) {
    container.innerHTML = `
        <div class="user-dashboard">
            <!-- Sidebar / Auth & Request Forms -->
            <div class="user-sidebar">
                
                <!-- Auth / Profile Mock -->
                <div class="glass-panel">
                    <div class="profile-header">
                        <div class="avatar">C</div>
                        <div>
                            <h3 style="margin-bottom: 4px;">Charan</h3>
                            <span class="text-muted">Student ID: #88291</span>
                        </div>
                        <button class="btn" style="padding: 6px; margin-left: auto;">⚙️</button>
                    </div>
                </div>

                <!-- Mission History Summary Mock -->
                <div class="glass-panel" style="flex: 1; overflow-y: auto;">
                    <h4>Recent History</h4>
                    <div class="flex-col" style="margin-top: 12px; gap: 8px;">
                        <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 6px; font-size: 0.85rem;">
                            <strong>Yesterday, 10:30 PM</strong><br/>
                            <span class="text-muted">Library to Dorm A (1.2 km)</span><br/>
                            <span class="text-success" style="font-size: 0.75rem;">✓ Safe Arrival • 0 Alerts</span>
                        </div>
                        <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 6px; font-size: 0.85rem;">
                            <strong>Mar 04, 11:15 PM</strong><br/>
                            <span class="text-muted">Engineering Bldg to Parking Lot (0.8 km)</span><br/>
                            <span class="text-success" style="font-size: 0.75rem;">✓ Safe Arrival • 0 Alerts</span>
                        </div>
                    </div>
                </div>

                <!-- Request Escort Form -->
                <div class="glass-panel request-panel">
                    <h2 class="text-accent" style="font-size: 1.1rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 8px;">Request Drone</h2>
                    <div class="form-group" style="margin-top: 12px;">
                        <label>Current Location</label>
                        <div style="display: flex; gap: 8px;">
                            <input type="text" class="form-input" value="Locating..." id="start-input" readonly style="flex: 1;">
                            <button class="btn" id="btn-locate" title="Get GPS">📍</button>
                        </div>
                    </div>
                    <div class="form-group" style="margin-top: 12px; position: relative;">
                        <label>Destination</label>
                        <input type="text" class="form-input" placeholder="e.g. Dormitory C, East Wing" id="dest-input" autocomplete="off">
                        <div id="dest-autocomplete-results" class="autocomplete-dropdown hidden"></div>
                    </div>
                    
                    <div class="form-group" style="margin-top: 12px;">
                        <label>Safe Zone Status</label>
                        <div style="display: flex; align-items: center; gap: 8px; padding: 8px; background: rgba(0, 255, 136, 0.1); border-radius: 6px; border: 1px solid var(--accent-green);">
                            <span class="status-dot"></span>
                            <span style="font-size: 0.85rem; color: var(--accent-green);">Inside Protected Campus Zone</span>
                        </div>
                    </div>

                    <button class="btn btn-primary w-full animate-pulse" style="margin-top: 20px; font-size: 1rem; padding: 12px;" id="btn-request">Deploy Drone</button>
                </div>
            </div>

            <!-- Main Map / Video Area -->
            <div class="user-main-area">
                
                <!-- Status Timeline -->
                <div class="glass-panel" style="padding: 10px 20px;">
                    <div class="timeline-strip">
                        <div class="timeline-step">Request Sent</div>
                        <div class="timeline-step">Drone Dispatched</div>
                        <div class="timeline-step">Drone Arriving</div>
                        <div class="timeline-step">Tracking Active</div>
                        <div class="timeline-step">Completed</div>
                    </div>
                </div>

                <!-- Live Viewport (Map/Camera) -->
                <div class="viewport-container" id="user-viewport" style="position: relative;">
                    <div id="user-map" style="position: absolute; top:0; left:0; right:0; bottom:0; border-radius: 12px; overflow: hidden;"></div>
                    
                    <!-- Overlays -->
                    <div class="map-overlay mission-stats glass-panel">
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px;">MISSION STATUS</div>
                        <div style="font-size: 1.2rem; font-weight: bold; color: var(--text-main);">Standby</div>
                        <div style="margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem;">
                            <div>
                                <div class="text-muted">ETA</div>
                                <div>--:--</div>
                            </div>
                            <div>
                                <div class="text-muted">Distance</div>
                                <div>-- mi</div>
                            </div>
                        </div>
                    </div>

                    <div class="map-overlay drone-status-widget glass-panel">
                        <span class="status-dot" style="background: var(--text-muted); box-shadow: none;" id="drone-conn-dot"></span>
                        <span style="font-size: 0.9rem; font-weight: 500;" id="drone-conn-text">No Drone Assigned</span>
                    </div>

                    <!-- Toggle Camera/Map -->
                    <div class="map-overlay glass-panel" style="top: var(--spacing-md); left: 50%; transform: translateX(-50%); padding: 6px; display: flex; gap: 4px;">
                        <button class="btn btn-primary" style="padding: 4px 12px; font-size: 0.8rem;">GPS Map</button>
                        <button class="btn" style="padding: 4px 12px; font-size: 0.8rem;">Live Camera</button>
                        <button class="btn" style="padding: 4px 12px; font-size: 0.8rem; margin-left: 8px;">Toggle AI Overlay</button>
                    </div>

                    <!-- Share / Panic Buttons -->
                    <div class="map-overlay glass-panel flex-row" style="bottom: var(--spacing-md); left: var(--spacing-md); padding: 8px;">
                        <button class="btn">🔗 Share Live Link</button>
                    </div>

                    <div class="map-overlay emergency-btn-container">
                        <button class="btn btn-danger btn-panic animate-pulse-danger" id="btn-panic">SOS</button>
                    </div>

                    <!-- Center Map Markers (Mock) -->
                    <div class="map-overlay" style="top: 50%; left: 50%; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; opacity: 0.5;">
                        <div style="width: 20px; height: 20px; background: var(--accent-blue); border-radius: 50%; box-shadow: 0 0 15px var(--accent-blue);"></div>
                        <span style="margin-top: 8px; font-size: 0.8rem; background: rgba(0,0,0,0.5); padding: 2px 6px; border-radius: 4px;">You</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Mock interactions
    const reqBtn = container.querySelector('#btn-request');
    const destInput = container.querySelector('#dest-input');
    
    reqBtn.addEventListener('click', () => {
        if(!destInput.value) {
            alert('Please enter a destination.');
            return;
        }
        
        reqBtn.textContent = "Deploying Drone...";
        reqBtn.classList.remove('animate-pulse');
        reqBtn.style.opacity = '0.7';

        // Mock state update
        setTimeout(() => {
            reqBtn.textContent = "Drone En Route";
            reqBtn.classList.remove('btn-primary');
            reqBtn.classList.add('btn');
            
            const steps = container.querySelectorAll('.timeline-step');
            steps[0].classList.add('active');
            steps[1].classList.add('active');

            const connDot = container.querySelector('#drone-conn-dot');
            const connText = container.querySelector('#drone-conn-text');
            connDot.style.background = 'var(--text-main)';
            connText.textContent = "Drone Sentry-04 Connected";
            connText.style.color = 'var(--text-main)';

            const statusPanel = container.querySelector('.mission-stats');
            statusPanel.innerHTML = `
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px;">MISSION STATUS</div>
                <div style="font-size: 1.2rem; font-weight: bold; color: var(--text-main);">Drone Dispatched</div>
                <div style="margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem;">
                    <div>
                        <div class="text-muted">ETA (Drone)</div>
                        <div class="text-main">2 mins</div>
                    </div>
                    <div>
                        <div class="text-muted">Distance (Drone)</div>
                        <div>0.4 mi</div>
                    </div>
                </div>
            `;
        }, 1500);
    });

    const panicBtn = container.querySelector('#btn-panic');
    panicBtn.addEventListener('click', () => {
        alert("🚨 EMERGENCY ALERT TRIGGERED! 🚨\n\nAdmin Control Center has been notified. Siren activated.");
        panicBtn.style.transform = 'scale(1.1)';
        panicBtn.style.boxShadow = '0 0 30px rgba(255, 51, 102, 1)';
    });

    // Initialize Mapbox Map & APIs
    setTimeout(() => {
        mapboxgl.accessToken = 'pk.eyJ1IjoiY2hhcmFua2FrdWxhIiwiYSI6ImNtbWd4aG9kNjBhNjQycHB0ZGc3ZHVtdjcifQ.hWbgSljS6hkSlh56nRuOrA';
        const userMap = new mapboxgl.Map({
            container: 'user-map', // container ID
            style: 'mapbox://styles/mapbox/dark-v11', // Mapbox Dark theme
            center: [-105.2705, 40.0150], // Starting position [lng, lat] for Boulder, CO
            zoom: 15,
            pitch: 45 // Add a slight tilt for a drone camera feel
        });

        // Setup 3D Buildings Layer
        userMap.on('style.load', () => {
            const layers = userMap.getStyle().layers;
            let labelLayerId;
            for (let i = 0; i < layers.length; i++) {
                if (layers[i].type === 'symbol' && layers[i].layout['text-field']) {
                    labelLayerId = layers[i].id;
                    break;
                }
            }
             
            userMap.addLayer({
                'id': 'add-3d-buildings',
                'source': 'composite',
                'source-layer': 'building',
                'filter': ['==', 'extrude', 'true'],
                'type': 'fill-extrusion',
                'minzoom': 14,
                'paint': {
                    'fill-extrusion-color': '#2a3a4a', 
                    'fill-extrusion-height': ['get', 'height'],
                    'fill-extrusion-base': ['get', 'min_height'],
                    'fill-extrusion-opacity': 0.8
                }
            }, labelLayerId);
        });

        // State variables for routing
        let startCoords = [-105.2705, 40.0150]; // Default boulder
        let destCoords = null;
        let routeLayerId = 'route-path-layer';
        
        // Custom 'user' marker
        const userMarkerEl = document.createElement('div');
        userMarkerEl.className = 'custom-marker-user';
        const userMarker = new mapboxgl.Marker({ element: userMarkerEl })
            .setLngLat(startCoords)
            .addTo(userMap);
            
        const destMarkerEl = document.createElement('div');
        destMarkerEl.className = 'custom-marker-drone'; // Re-use for dest temporarily
        destMarkerEl.style.backgroundColor = 'var(--accent-green)';
        const destMarker = new mapboxgl.Marker({ element: destMarkerEl });

        // Step 1: Geolocation for Start Input
        const startInput = container.querySelector('#start-input');
        const btnLocate = container.querySelector('#btn-locate');
        
        const reverseGeocode = async (lng, lat) => {
            try {
                const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?access_token=${mapboxgl.accessToken}&types=address,poi`;
                const res = await fetch(url);
                const data = await res.json();
                if(data.features && data.features.length > 0) {
                    startInput.value = data.features[0].place_name;
                } else {
                    startInput.value = "Unknown Location";
                }
            } catch {
                startInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
            }
        };

        const getUserLocation = async () => {
            startInput.value = "Requesting permission...";
            
            const fallbackToIP = async () => {
                try {
                    startInput.value = "Estimating from Network...";
                    const res = await fetch('https://ipapi.co/json/');
                    const data = await res.json();
                    if(data.latitude && data.longitude) {
                        startCoords = [data.longitude, data.latitude];
                        userMarker.setLngLat(startCoords);
                        userMap.flyTo({ center: startCoords, zoom: 12 });
                        startInput.value = `${data.city}, ${data.region}`;
                    } else {
                        throw new Error("IP location failed");
                    }
                } catch (e) {
                    console.warn("IP Fallback failed", e);
                    startInput.value = "University Library, North Ent. (Default)";
                }
            };
            
            const useElectronGPS = async () => {
                try {
                    const loc = await window.ipcRenderer.getAppLocation();
                    if(loc && loc.lat && loc.lng) {
                         startCoords = [loc.lng, loc.lat];
                         userMarker.setLngLat(startCoords);
                         userMap.flyTo({ center: startCoords, zoom: 16 });
                         reverseGeocode(loc.lng, loc.lat);
                         return true;
                    }
                } catch(e) { console.warn('IPC GPS failed'); }
                return false;
            };

            // 1. Try secure IPC (Electron)
            if (window.ipcRenderer && window.ipcRenderer.getAppLocation) {
                const success = await useElectronGPS();
                if(success) return;
            }

            // 2. Try native browser (Will fail on HTTP Localhost)
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lng = position.coords.longitude;
                        const lat = position.coords.latitude;
                        startCoords = [lng, lat];
                        userMarker.setLngLat(startCoords);
                        userMap.flyTo({ center: startCoords, zoom: 16 });
                        reverseGeocode(lng, lat);
                    },
                    (error) => {
                        console.warn("Geolocation failed", error);
                        // 3. Fallback to IP address geolocation
                        fallbackToIP();
                    },
                    { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
                );
            } else {
                fallbackToIP();
            }
        };
        
        btnLocate.addEventListener('click', getUserLocation);
        getUserLocation(); // Auto locate on mount

        // Step 2: Destination Autocomplete
        const autocompleteResults = container.querySelector('#dest-autocomplete-results');
        let currentTimeout;

        destInput.addEventListener('input', (e) => {
            const query = e.target.value;
            if(!query) {
                autocompleteResults.classList.add('hidden');
                return;
            }
            
            clearTimeout(currentTimeout);
            currentTimeout = setTimeout(async () => {
                try {
                    // Allow broad global search like Google Maps
                    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${mapboxgl.accessToken}&autocomplete=true&limit=5`;
                    const res = await fetch(url);
                    const data = await res.json();
                    
                    autocompleteResults.innerHTML = '';
                    if(data.features && data.features.length > 0) {
                        data.features.forEach(feat => {
                            const item = document.createElement('div');
                            item.className = 'autocomplete-item';
                            // Safe parsing of address
                            let subtext = feat.place_name;
                            if(feat.place_name.startsWith(feat.text)) {
                                subtext = feat.place_name.substring(feat.text.length).replace(/^,\s*/, '');
                            }
                            item.innerHTML = `<strong>${feat.text}</strong><span style="font-size: 0.75rem; color: var(--text-muted);">${subtext}</span>`;
                            
                            item.addEventListener('click', () => {
                                destInput.value = feat.place_name;
                                destCoords = feat.center; // [lng, lat]
                                autocompleteResults.classList.add('hidden');
                                
                                // Show destination marker & recenter map
                                destMarker.setLngLat(destCoords).addTo(userMap);
                                
                                // Fit bounds to show both start and end
                                const bounds = new mapboxgl.LngLatBounds(startCoords, startCoords);
                                bounds.extend(destCoords);
                                userMap.fitBounds(bounds, { padding: 80, maxZoom: 16 });
                            });
                            
                            autocompleteResults.appendChild(item);
                        });
                        autocompleteResults.classList.remove('hidden');
                    } else {
                        autocompleteResults.classList.add('hidden');
                    }
                } catch(e) {
                    console.error("Geocoding err", e);
                }
            }, 300); // Debounce
        });
        
        // Hide autocomplete on click outside
        document.addEventListener('click', (e) => {
            if(!destInput.contains(e.target) && !autocompleteResults.contains(e.target)) {
                autocompleteResults.classList.add('hidden');
            }
        });

        // Step 3: Draw Route on Deploy
        const drawRoute = async () => {
            if(!destCoords) return;
            
            try {
                // Get directions using mapbox directions API (walking profile)
                const url = `https://api.mapbox.com/directions/v5/mapbox/walking/${startCoords[0]},${startCoords[1]};${destCoords[0]},${destCoords[1]}?geometries=geojson&access_token=${mapboxgl.accessToken}`;
                const res = await fetch(url);
                const data = await res.json();
                
                if(data.routes && data.routes.length > 0) {
                    const route = data.routes[0];
                    const routeGeoJSON = {
                        type: 'Feature',
                        properties: {},
                        geometry: route.geometry
                    };
                    
                    // Add source and layer for line
                    if (userMap.getSource('route-source')) {
                        userMap.getSource('route-source').setData(routeGeoJSON);
                    } else {
                        userMap.addSource('route-source', {
                            type: 'geojson',
                            data: routeGeoJSON
                        });
                        
                        userMap.addLayer({
                            id: routeLayerId,
                            type: 'line',
                            source: 'route-source',
                            layout: {
                                'line-join': 'round',
                                'line-cap': 'round'
                            },
                            paint: {
                                'line-color': '#00f0ff', // Glowing cyan
                                'line-width': 5,
                                'line-opacity': 0.9
                            }
                        }, 'add-3d-buildings'); // Draw below labels but above everything else
                    }
                    
                    // Fit bounds to show the entire route safely
                    const coordinates = route.geometry.coordinates;
                    const bounds = new mapboxgl.LngLatBounds(
                        coordinates[0],
                        coordinates[0]
                    );
                    for (const coord of coordinates) {
                        bounds.extend(coord);
                    }
                    userMap.fitBounds(bounds, {
                        padding: {top: 100, bottom: 150, left: 100, right: 350}, // Accommodate overlays
                        maxZoom: 16
                    });
                    
                    // Update stats panel
                    const distanceMiles = (route.distance / 1609.34).toFixed(2);
                    const durationMins = Math.ceil(route.duration / 60);
                    
                    const statusPanel = container.querySelector('.mission-stats');
                    statusPanel.innerHTML = `
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px;">MISSION STATUS</div>
                        <div style="font-size: 1.2rem; font-weight: bold; color: var(--text-main);">Drone Dispatched</div>
                        <div style="margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem;">
                            <div>
                                <div class="text-muted">ETA (Drone)</div>
                                <div class="text-main" style="color:var(--accent-cyan);">${durationMins} mins</div>
                            </div>
                            <div>
                                <div class="text-muted">Distance</div>
                                <div>${distanceMiles} mi</div>
                            </div>
                        </div>
                    `;
                } else {
                    console.warn("No walking routes found.");
                }
            } catch(e) {
                console.error("Routing err", e);
            }
        };

        // Hook into the existing Deploy Drone mock click logic defined earlier 
        // We override the timeout in reqBtn click listener slightly to trigger the router
        const originalBtnClick = reqBtn.onclick; 
        // Rather than overriding, we mutate the listener... wait, JS event listeners compound.
        // We will just listen again and it triggers simultaneously.
        reqBtn.addEventListener('click', () => {
            if(!destCoords) return;
            // Draw route line
            drawRoute();
        });

    }, 100);
}
