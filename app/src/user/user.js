import './user.css';

export function renderUserView(container) {
    container.innerHTML = `
        <div class="user-dashboard">
            <!-- Sidebar / Auth & Request Forms -->
            <div class="user-sidebar">
                
                <!-- REQUEST AEGIS CARD -->
                <div class="glass-panel request-card" style="display: flex; flex-direction: column; gap: 20px;">
                    <div style="font-size: 1.15rem; letter-spacing: 1px; color: var(--text-main); font-weight: bold; text-transform: uppercase;">Request AEGIS</div>
                    
                    <div class="form-group">
                        <label>CURRENT LOCATION</label>
                        <input type="text" class="form-input" value="University & Broadway" id="start-input" readonly>
                        <button class="btn hidden" id="btn-locate" style="display:none;"></button>
                    </div>
                    
                    <div class="form-group" style="position: relative;">
                        <label>DESTINATION</label>
                        <input type="text" class="form-input" placeholder="E.G." id="dest-input" autocomplete="off">
                        <div id="dest-autocomplete-results" class="autocomplete-dropdown hidden"></div>
                    </div>
                    
                    <button class="btn btn-deploy" id="btn-request" style="display: flex; align-items: center; justify-content: center; gap: 8px; padding-right: 16px; text-transform: none; font-size: 1rem; font-weight: 600;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"></polygon></svg>
                        Request Drone Escort
                    </button>

                    <button class="btn" id="btn-emergency-sos" style="background-color: #ff3b30; color: white; border: none; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-transform: none; font-size: 1rem; font-weight: 600; padding: 12px 0;">
                        <span>Emergency SOS</span>
                        <span style="font-size: 0.65rem; font-weight: 500; opacity: 0.9; margin-top: 2px;">5-second safety activation</span>
                    </button>

                    <button id="btn-alert-friends" class="btn" style="background-color: #ff9500; color: white; border: none; border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 8px; text-transform: none; font-size: 1rem; font-weight: 600; padding: 12px 0;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                        Alert Friends
                    </button>

                    <button id="btn-add-friends" class="btn" style="background-color: #0a7aff; color: white; border: none; border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 8px; text-transform: none; font-size: 1rem; font-weight: 600; padding: 12px 0;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                        Add Friends
                    </button>
                    
                    <div style="text-align: center; margin-top: auto; font-size: 0.70rem; color: rgba(255, 255, 255, 0.4); font-weight: 500; letter-spacing: 0.5px; padding-bottom: 5px;">
                        AEGIS Autonomous Escort System
                    </div>

                </div>
            </div>

            <!-- Main Map Area -->
            <div class="user-main-area" style="position: relative;">
                
                <!-- Status Timeline Hovering Above Map -->
                <div class="timeline-pill-container" style="position: absolute; top: -3px; left: 50%; transform: translateX(-50%); z-index: 100;">
                    <div class="timeline-pill glass-panel-dark" id="drone-timeline">
                        <span id="ts-req" class="active">REQUEST</span> <span class="arrow">&gt;</span>
                        <span id="ts-disp">DISPATCHED</span> <span class="arrow">&gt;</span>
                        <span id="ts-foll">FOLLOWING</span> <span class="arrow">&gt;</span>
                        <span id="ts-arr">ARRIVED</span>
                    </div>
                </div>

                <!-- Live Viewport (Map) -->
                <div class="viewport-container" id="user-viewport">
                    <div id="user-map" style="position: absolute; top:0; left:0; right:0; bottom:0; border-radius: inherit;"></div>
                    

                    
                    <div class="map-overlay eta-pill-tr glass-panel-dark">
                        <div style="display: flex; gap: 15px; justify-content: space-between; align-items: center; width: 100%;">
                            <div>
                                <div class="text-muted" style="font-size: 0.65rem; letter-spacing: 0.5px;">ETA:</div>
                                <div style="font-weight: 500; font-size: 0.85rem; letter-spacing: 0.5px;" id="stat-eta-top">-- min</div>
                            </div>
                            <div class="bars"><span></span><span></span><span class="dim"></span><span class="dim"></span><span class="dim"></span></div>
                        </div>
                    </div>
                    
                    <!-- Picture in Picture AEGIS Feed -->
                    <div class="pip-container glass-panel-dark">
                        <div class="pip-video-feed">
                            <div class="scanlines"></div>
                            <img id="tello-stream" src="http://127.0.0.1:5505/video_feed" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 1; opacity: 0.8;" onerror="this.src=''; this.alt='Awaiting connection...';" alt="" />
                            
                            <!-- HUD Overlays -->
                            <div class="hud-top-left"><span class="rec-dot"></span> REC</div>
                            <div class="hud-top-right">HDG: NW</div>
                            <div class="hud-bottom-left">BATT: 84%</div>
                            <div class="hud-bottom-right">GPS Lock</div>
                            
                            <div class="hud-left-edge">ALT: 15m</div>
                            <div class="hud-right-edge">SPD: 8km/h</div>
                            <div class="hud-horizon-line"></div>
                            
                            <!-- Target Lock Center -->
                            <div class="target-lock">
                                <div class="tl-circle"></div>
                                <div class="tl-crosshair"></div>
                            </div>
                            
                            <!-- Interactivity Controls -->
                            <div class="pip-controls">
                                <button id="btn-thermal" title="Thermal View">🔆</button>
                                <button id="btn-fullscreen" title="Full Screen">⛶</button>
                            </div>
                        </div>
                    </div>
                    
                </div>
            </div>
            
            <!-- Emergency SOS Overlay -->
            <div id="sos-overlay" class="sos-overlay">
                <div class="sos-overlay-header">
                    <button id="sos-back-btn" class="sos-back-btn">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
                    </button>
                </div>
                
                <div class="sos-content-box">
                    <div class="sos-warning-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" width="64" height="64"><path d="M12 2L1 21h22L12 2zm1 14h-2v2h2v-2zm0-6h-2v4h2v-4z"></path></svg>
                    </div>
                    
                    <h2 style="font-size: 1.5rem; font-weight: bold; margin-bottom: 8px; letter-spacing: 0px;">Emergency Alert Ready</h2>
                    <p style="font-size: 0.9rem; font-weight: 500; opacity: 0.9; margin-bottom: 24px;">AEGIS drone entering priority mode</p>
                    
                    <h3 id="sos-countdown-text" style="font-size: 1.25rem; font-weight: bold; margin-bottom: 15px;">Activating in 5s</h3>
                    
                    <div class="sos-checklist-box">
                        <div class="sos-check-item" id="sos-chk-1">
                            <div class="sos-circle"></div> <span>Sharing location with campus safety</span>
                        </div>
                        <div class="sos-check-item" id="sos-chk-2">
                            <div class="sos-circle"></div> <span>Notifying emergency contact</span>
                        </div>
                        <div class="sos-check-item" id="sos-chk-3">
                            <div class="sos-circle"></div> <span>Dispatching AEGIS drone</span>
                        </div>
                    </div>
                </div>
                
                <button id="btn-cancel-sos" class="btn-cancel-sos">Cancel Emergency</button>
            </div>
            
            <!-- Add Friends Overlay -->
            <div id="add-friends-overlay" class="add-friends-overlay">
                <div class="add-friends-overlay-header">
                    <button id="add-friends-back-btn" class="sos-back-btn" style="background: rgba(255, 255, 255, 0.15); color: white;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
                    </button>
                </div>
                
                <div class="add-friends-content-box">
                    <h2 style="font-size: 1.8rem; font-weight: bold; margin-bottom: 12px; letter-spacing: 0.5px;">Add Friends</h2>
                    <p style="font-size: 0.95rem; font-weight: 500; color: #b0b0b0; line-height: 1.4; max-width: 250px; margin: 0 auto 30px auto;">Invite friends so they can be alerted during an escort.</p>
                    
                    <div class="friends-list-container">
                        <div class="friend-item">
                            <div class="friend-avatar" style="background: #2c2c2e;">A</div>
                            <div class="friend-info">
                                <div class="friend-name">Alice Johnson</div>
                            </div>
                            <button class="btn-add-friend-action">Add</button>
                        </div>
                        
                        <!-- Dummy Contact Item -->
                        <div class="friend-item">
                            <div class="friend-avatar" style="background: #2c2c2e;">B</div>
                            <div class="friend-info">
                                <div class="friend-name">Bob Smith</div>
                            </div>
                            <button class="btn-add-friend-action">Add</button>
                        </div>
                        
                        <!-- Dummy Contact Item -->
                        <div class="friend-item">
                            <div class="friend-avatar" style="background: #2c2c2e;">C</div>
                            <div class="friend-info">
                                <div class="friend-name">Charlie Davis</div>
                            </div>
                            <button class="btn-add-friend-action">Add</button>
                        </div>
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
        
        reqBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"></polygon></svg>DEPLOYING...`;
        reqBtn.classList.remove('animate-pulse');
        reqBtn.style.opacity = '0.7';

        // Mock State Update: Request -> Dispatched
        const tlReq = container.querySelector('#ts-req');
        const tlDisp = container.querySelector('#ts-disp');
        const tlFoll = container.querySelector('#ts-foll');
        const tlArr = container.querySelector('#ts-arr');
        
        // Remove old actives
        [tlReq, tlDisp, tlFoll, tlArr].forEach(el => { if(el) el.classList.remove('active'); });
        
        // Setup progression sequence
        if(tlDisp) tlDisp.classList.add('active');

        setTimeout(() => {
            reqBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11"></polygon></svg>Request Drone Escort`;
            reqBtn.style.opacity = '1';
            
            [tlReq, tlDisp, tlFoll, tlArr].forEach(el => { if(el) el.classList.remove('active'); });
            if(tlFoll) tlFoll.classList.add('active');
            
            // For demo purposes, the drone will stay in "FOLLOWING" mode and never reach "ARRIVED"
        }, 1500);
    });

    const sosBtn = container.querySelector('#btn-emergency-sos');
    const sosOverlay = container.querySelector('#sos-overlay');
    const sosBackBtn = container.querySelector('#sos-back-btn');
    const sosCancelBtn = container.querySelector('#btn-cancel-sos');
    const sosCountdownText = container.querySelector('#sos-countdown-text');
    const sosChk1 = container.querySelector('#sos-chk-1');
    const sosChk2 = container.querySelector('#sos-chk-2');
    const sosChk3 = container.querySelector('#sos-chk-3');
    
    let sosTimer = null;
    
    const setChecked = (el) => {
        el.classList.add('checked');
        el.querySelector('.sos-circle').innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    };

    sosBtn.addEventListener('click', () => {
        sosOverlay.classList.add('active');
        sosCountdownText.textContent = 'Activating in 5s';
        [sosChk1, sosChk2, sosChk3].forEach(chk => {
            chk.classList.remove('checked');
            chk.querySelector('.sos-circle').innerHTML = '';
        });
        
        let timeLeft = 5;
        
        sosTimer = setInterval(() => {
            timeLeft--;
            if (timeLeft > 0) {
                sosCountdownText.textContent = `Activating in ${timeLeft}s`;
                if (timeLeft === 4) setChecked(sosChk1);
                if (timeLeft === 2) setChecked(sosChk2);
                if (timeLeft === 1) setChecked(sosChk3);
            } else {
                clearInterval(sosTimer);
                sosOverlay.classList.remove('active');
                
                // Dispatch event for Admin Dashboard to catch
                window.dispatchEvent(new CustomEvent('aegis-sos-triggered'));
                
                setTimeout(() => alert('Emergency Services Notified.'), 100);
            }
        }, 1000);
    });

    const cancelSos = () => {
        clearInterval(sosTimer);
        sosOverlay.classList.remove('active');
    };

    sosBackBtn.addEventListener('click', cancelSos);
    sosCancelBtn.addEventListener('click', cancelSos);
    
    // Add Friends Overlay Logic
    const friendsBtn = container.querySelector('#btn-add-friends');
    const friendsOverlay = container.querySelector('#add-friends-overlay');
    const friendsBackBtn = container.querySelector('#add-friends-back-btn');

    if (friendsBtn && friendsOverlay && friendsBackBtn) {
        friendsBtn.addEventListener('click', () => {
            friendsOverlay.classList.add('active');
        });
        friendsBackBtn.addEventListener('click', () => {
            friendsOverlay.classList.remove('active');
        });
        
        // Add button logic
        const addFriendButtons = friendsOverlay.querySelectorAll('.btn-add-friend-action');
        addFriendButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                if (!btn.classList.contains('added')) {
                    btn.classList.add('added');
                    btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                } else {
                    btn.classList.remove('added');
                    btn.innerHTML = 'Add';
                }
            });
        });
    }

    const alertFriendsBtn = container.querySelector('#btn-alert-friends');
    if (alertFriendsBtn) {
        alertFriendsBtn.addEventListener('click', () => {
            alert('Friends have been alerted!');
        });
    }
    
    // PIP Interactivity Controls
    const btnThermal = container.querySelector('#btn-thermal');
    const telloStream = container.querySelector('#tello-stream');
    let isThermal = false;
    btnThermal.addEventListener('click', () => {
        isThermal = !isThermal;
        if(isThermal) {
            telloStream.classList.add('thermal-mode');
            btnThermal.style.color = '#ff3366';
        } else {
            telloStream.classList.remove('thermal-mode');
            btnThermal.style.color = '';
        }
    });

    const btnFullscreen = container.querySelector('#btn-fullscreen');
    const pipContainer = container.querySelector('.pip-container');
    let isFullscreen = false;
    btnFullscreen.addEventListener('click', () => {
        isFullscreen = !isFullscreen;
        if(isFullscreen) {
            pipContainer.classList.add('pip-fullscreen');
            btnFullscreen.style.color = '#ff3366';
        } else {
            pipContainer.classList.remove('pip-fullscreen');
            btnFullscreen.style.color = '';
        }
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
        
        // Fix for Mapbox sizing bug when loaded inside a hidden/flex container
        setTimeout(() => {
            userMap.resize();
        }, 200);

            // Setup 3D Buildings Layer as glowing wireframes
            userMap.on('style.load', () => {
                const layers = userMap.getStyle().layers;
                let labelLayerId;
                for (let i = 0; i < layers.length; i++) {
                    if (layers[i].type === 'symbol' && layers[i].layout['text-field']) {
                        labelLayerId = layers[i].id;
                        break;
                    }
                }
                 
                // Wireframe glowing buildings
                userMap.addLayer({
                    'id': 'add-3d-buildings',
                    'source': 'composite',
                    'source-layer': 'building',
                    'filter': ['==', 'extrude', 'true'],
                    'type': 'fill-extrusion',
                    'minzoom': 14,
                    'paint': {
                        'fill-extrusion-color': '#0d1620', // Very dark blue/black
                        'fill-extrusion-height': ['get', 'height'],
                        'fill-extrusion-base': ['get', 'min_height'],
                        'fill-extrusion-opacity': 0.7
                    }
                }, labelLayerId);
                
                // Hack to create glowing outlines for 3D buildings by duplicating the layer with lines isn't natively supported for extrusion.
                // But we can add a flat line layer to simulate ground topology.
                userMap.addLayer({
                    'id': 'building-outlines',
                    'source': 'composite',
                    'source-layer': 'building',
                    'filter': ['==', 'extrude', 'true'],
                    'type': 'line',
                    'minzoom': 14,
                    'paint': {
                        'line-color': '#00f0ff',
                        'line-width': 1,
                        'line-opacity': 0.5
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
        userMarkerEl.innerHTML = '<div class="pulse-ring"></div><div class="user-center">YOU</div>';
        
        const userMarker = new mapboxgl.Marker({ element: userMarkerEl })
            .setLngLat(startCoords)
            .addTo(userMap);
            
        const destMarkerEl = document.createElement('div');
        destMarkerEl.className = 'custom-marker-drone'; // Temporarily the destination marker
        destMarkerEl.innerHTML = '<span style="color:#00f0ff;font-size:1.5rem;">❖</span>';
        const destMarker = new mapboxgl.Marker({ element: destMarkerEl });
        
        // Sentry 2 stationary display
        const sentry2El = document.createElement('div');
        sentry2El.className = 'sentry-marker';
        sentry2El.innerHTML = '<div class="sentry-icon">✈</div><div class="sentry-label">SENTRY-02</div>';
        // We'll place this just north east of the start location
        const sentry2Coords = [startCoords[0] + 0.003, startCoords[1] + 0.003];
        new mapboxgl.Marker({ element: sentry2El }).setLngLat(sentry2Coords).addTo(userMap);

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
            startInput.value = "Acquiring GPS Lock...";
            
            // For hackathon/demo purposes, instantly resolve to the requested "Eaton Humanities" building at CU Boulder
            setTimeout(() => {
                const lng = -105.271811;
                const lat = 40.008987;
                startCoords = [lng, lat];
                if (userMarker) userMarker.setLngLat(startCoords);
                if (userMap) userMap.flyTo({ center: startCoords, zoom: 16 });
                
                startInput.value = "Eaton Humanities - 1610 Pleasant St, Boulder, CO 80309";
            }, 600); // Small delay to simulate the "lock" loading text
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
                    // Use OpenStreetMap Nominatim API for Google Maps level precision on college campuses and buildings
                    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query + " Boulder")}&format=json&viewbox=-105.32,40.06,-105.20,39.96&bounded=1&limit=6`;
                    const res = await fetch(url, {
                        headers: {
                            'Accept': 'application/json',
                            'User-Agent': 'HackCU-Drone-App'
                        }
                    });
                    const data = await res.json();
                    
                    autocompleteResults.innerHTML = '';
                    const allResults = [];

                    if(Array.isArray(data) && data.length > 0) {
                        data.forEach(feat => {
                            let subtext = feat.display_name.replace(feat.name + ', ', '');
                            
                            allResults.push({
                                text: feat.name,
                                subtext: subtext,
                                place_name: feat.name,
                                center: [parseFloat(feat.lon), parseFloat(feat.lat)]
                            });
                        });
                    }

                    if(allResults.length > 0) {
                        allResults.forEach(feat => {
                            const item = document.createElement('div');
                            item.className = 'autocomplete-item';
                            item.innerHTML = `<strong>${feat.text}</strong><span style="font-size: 0.72rem; color: var(--text-muted); padding-left: 8px;">${feat.subtext}</span>`;
                            
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
                    
                    const durationMins = Math.ceil(route.duration / 60);
                    const etaTop = container.querySelector('#stat-eta-top');
                    const etaBot = container.querySelector('#stat-eta-bot');
                    if(etaTop) etaTop.textContent = `${durationMins} min`;
                    if(etaBot) etaBot.textContent = `${durationMins} min`;
                    
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
