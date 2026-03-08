import './admin.css';

export function renderAdminView(container) {
    const fleetDrones = [
        { id: 'AEGIS-01', status: 'Active Tracking', battery: 82, lat: 40.0160, lng: -105.2805, color: '#00f0ff', ai: 'STUDENT (ESCORT SECURED) [98%]', telemetry: 'ALT: 45ft<br>SPD: 12mph<br>GPS: LOCK', vid: 'https://picsum.photos/seed/aegis1/800/600', isCritical: false },
        { id: 'AEGIS-02', status: 'Hover / Idle', battery: 95, lat: 40.0110, lng: -105.2605, color: '#00f0ff', ai: 'NO TARGET [SCANNING]', telemetry: 'ALT: 120ft<br>SPD: 0mph<br>GPS: LOCK', vid: 'https://picsum.photos/seed/aegis2/800/600', isCritical: false },
        { id: 'AEGIS-03', status: 'Charging at Base', battery: 14, lat: 40.0180, lng: -105.2715, color: '#ff3366', ai: 'OFFLINE / CHARGING', telemetry: 'ALT: 0ft<br>SPD: 0mph<br>GPS: DOCK', vid: '/charging_station.png', isCritical: true },
        { id: 'AEGIS-04', status: 'Hover / Idle', battery: 60, lat: 40.0050, lng: -105.2650, color: '#00f0ff', ai: 'NO TARGET [SCANNING]', telemetry: 'ALT: 80ft<br>SPD: 0mph<br>GPS: LOCK', vid: 'https://picsum.photos/seed/street/800/600', isCritical: false },
        { id: 'AEGIS-05', status: 'Returning to Base', battery: 20, lat: 40.0080, lng: -105.2750, color: '#ff9500', ai: 'NAVIGATING TO DOCK', telemetry: 'ALT: 100ft<br>SPD: 22mph<br>GPS: LOCK', vid: 'https://picsum.photos/seed/building/800/600', isCritical: true },
        { id: 'AEGIS-06', status: 'Hover / Idle', battery: 88, lat: 40.0200, lng: -105.2600, color: '#00f0ff', ai: 'NO TARGET [SCANNING]', telemetry: 'ALT: 150ft<br>SPD: 0mph<br>GPS: LOCK', vid: 'https://picsum.photos/seed/aegis6/800/600', isCritical: false },
        { id: 'AEGIS-07', status: 'Charging at Base', battery: 100, lat: 40.0185, lng: -105.2725, color: '#ff3366', ai: 'OFFLINE / STANDBY', telemetry: 'ALT: 0ft<br>SPD: 0mph<br>GPS: DOCK', vid: '/charging_station.png', isCritical: false },
    ];

    container.innerHTML = `
        <div class="admin-dashboard overview-mode">
            
            <!-- Left Sidebar: Fleet & Controls -->
            <div class="admin-sidebar-left">
                <!-- Fleet Overview -->
                <div class="glass-panel" style="flex: 1; display: flex; flex-direction: column;">
                    <div class="space-between flex-row" style="margin-bottom: var(--spacing-md); border-bottom: 1px solid var(--border-subtle); padding-bottom: 8px;">
                        <h2 class="text-accent" style="margin-bottom: 0;">Fleet Status</h2>
                        <span class="text-muted" style="font-size: 0.8rem;">2 Active / 7 Total</span>
                    </div>
                    
                    <div class="flex-col" id="fleet-list-container" style="gap: 8px; overflow-y: auto;">
                        <div class="drone-list-item selected" id="btn-fleet-overview" style="background: rgba(0, 240, 255, 0.1); border-color: var(--accent-cyan);">
                            <div style="width: 100%; text-align: center;">
                                <div style="font-weight: bold; font-size: 1.1rem; color: #fff;">🌐 Fleet Overview</div>
                            </div>
                        </div>

                        ${fleetDrones.map((d, index) => `
                            <div class="drone-list-item" data-index="${index}" style="${d.isCritical ? 'opacity: 0.6;' : ''}">
                                <div>
                                    <div style="font-weight: bold;">${d.id}</div>
                                    <div class="${d.isCritical ? 'text-danger' : 'text-muted'}" style="font-size: 0.75rem;">Status: ${d.status}</div>
                                </div>
                                <div style="text-align: right;">
                                    <span class="${d.battery <= 20 ? 'text-danger' : 'text-success'}" style="font-size: 0.8rem;">${d.battery}%</span>
                                    <div class="battery-bar"><div class="battery-fill ${d.battery <= 20 ? 'critical' : ''}" style="width: ${d.battery}%;"></div></div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>

            <!-- Middle Main Area: Video & Global Map -->
            <div class="admin-main-area">


                <!-- Live Monitoring Video Grid -->
                <div class="video-grid">
                    
                    <!-- Overview Stats Panel (Shown in Overview Mode) -->
                    <div id="overview-stats-panel" class="video-feed" style="background: rgba(0, 20, 30, 0.4); border-color: var(--accent-cyan); display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px;">
                        <h2 style="color: var(--accent-cyan); margin-bottom: 24px;">Fleet Operations Metrics</h2>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; width: 100%; padding-top: 10px;">
                            <div class="glass-panel" style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px 10px; border-color: rgba(0, 240, 255, 0.2); background: rgba(0, 20, 30, 0.3); box-shadow: 0 4px 16px rgba(0,0,0,0.2);">
                                <div class="text-muted" style="font-size: 0.70rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; text-align: center;">Response Time</div>
                                <div style="font-size: 2.2rem; font-weight: 800; color: #fff; line-height: 1; text-shadow: 0 0 10px rgba(255,255,255,0.2);">1.2<span style="font-size: 1rem; color: var(--accent-cyan); margin-left: 4px; font-weight: 600;">min</span></div>
                            </div>
                            <div class="glass-panel" style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px 10px; border-color: rgba(0, 255, 136, 0.2); background: rgba(0, 30, 20, 0.3); box-shadow: 0 4px 16px rgba(0,0,0,0.2);">
                                <div class="text-muted" style="font-size: 0.70rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; text-align: center;">Active Users</div>
                                <div style="font-size: 2.2rem; font-weight: 800; color: var(--accent-green); line-height: 1; text-shadow: 0 0 15px rgba(0, 255, 136, 0.4);">124</div>
                            </div>
                            <div class="glass-panel" style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px 10px; border-color: rgba(255, 255, 255, 0.05); background: rgba(255, 255, 255, 0.02); box-shadow: 0 4px 16px rgba(0,0,0,0.2);">
                                <div class="text-muted" style="font-size: 0.70rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; text-align: center;">Total Patrolled</div>
                                <div style="font-size: 2.2rem; font-weight: 800; color: #fff; line-height: 1;">12.4<span style="font-size: 1rem; color: rgba(255,255,255,0.4); margin-left: 4px; font-weight: 600;">mi</span></div>
                            </div>
                            <div class="glass-panel" style="display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px 10px; border-color: rgba(0, 240, 255, 0.2); background: rgba(0, 20, 30, 0.3); box-shadow: 0 4px 16px rgba(0,0,0,0.2);">
                                <div class="text-muted" style="font-size: 0.70rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; text-align: center;">Available Units</div>
                                <div style="font-size: 2.2rem; font-weight: 800; color: var(--accent-cyan); line-height: 1; text-shadow: 0 0 15px rgba(0, 240, 255, 0.4);">4<span style="font-size: 1rem; color: rgba(255,255,255,0.4); margin-left: 4px; font-weight: 600;">/ 7</span></div>
                            </div>
                        </div>
                    </div>

                    <!-- Feed 1 (Active) (Shown in Drone Mode) -->
                    <div id="drone-video-panel" class="video-feed" style="border-color: var(--accent-cyan); box-shadow: 0 0 15px rgba(0, 240, 255, 0.1); overflow: hidden; position: relative;">
                        <div id="active-feed-media" class="ken-burns" style="position: absolute; inset: -10%; background: url('${fleetDrones[0].vid}') no-repeat center center/cover; filter: grayscale(50%) contrast(1.2); opacity: 0.6; transition: background 0.5s;"></div>
                        
                        <div id="active-feed-overlay" class="video-overlay" style="z-index: 1;">${fleetDrones[0].id} : ${fleetDrones[0].status.toUpperCase()} : REC</div>
                        
                        <!-- Mock AI Box Outline -->
                        <div class="ai-box animate-pulse" style="width: 250px; height: 160px; top: 30%; left: 40%; z-index: 1;">
                            <div id="active-ai-label" class="ai-label">${fleetDrones[0].ai}</div>
                        </div>

                        <div style="color: rgba(255,255,255,0.2); font-family: monospace; z-index: 1;">[No Physical Camera Attached]</div>
                        
                        <!-- Telemetry Overlay Bottom right -->
                        <div id="active-telemetry" style="position: absolute; bottom: 10px; right: 10px; text-align: right; font-family: monospace; font-size: 0.8rem; color: var(--accent-cyan); background: rgba(0,0,0,0.5); padding: 4px; z-index: 1;">
                            ${fleetDrones[0].telemetry}
                        </div>
                    </div>

                    <!-- Global Map Mock -->
                    <div class="video-feed" style="background: #111; position: relative;">
                        <div id="admin-map" style="position: absolute; top:0; left:0; right:0; bottom:0; border-radius: 8px;"></div>
                        <div class="video-overlay" style="color: var(--accent-green); border-color: rgba(0,255,136,0.3); z-index: 10;">FLEET OVERVIEW MAP</div>
                    </div>
                </div>
            </div>

            <!-- Right Sidebar: Alerts & Logs -->
            <div class="admin-sidebar-right">
                
                <!-- Emergency Alerts -->
                <div class="glass-panel" style="border-color: var(--accent-red);">
                    <h2 class="text-danger" style="margin-bottom: 8px;">🚨 Active Alerts</h2>
                    <div style="background: rgba(255, 51, 102, 0.1); border: 1px solid rgba(255, 51, 102, 0.3); padding: 10px; border-radius: 6px; font-size: 0.85rem; margin-top: 10px;" class="animate-pulse-danger hidden" id="mock-alert-box">
                        <strong style="font-size: 1rem; color: #ff3366;">🚨 EMERGENCY SOS ACTIVATED</strong><br>
                        <div style="margin: 8px 0; padding: 8px; background: rgba(0,0,0,0.2); border-radius: 4px;">
                            <strong>Drone:</strong> AEGIS-01<br>
                            <strong>Loc:</strong> North Quad Path<br>
                        </div>
                        <div style="margin: 8px 0; color: #34C759; font-weight: 500;">
                            ✓ Location Shared<br>
                            ✓ Campus Safety Notified<br>
                        </div>
                        <button class="btn btn-danger w-full" style="margin-top: 8px; padding: 8px; border-radius: 8px; font-weight: bold; background: #ff3b30;">Acknowledge & Deploy Ground Team</button>
                    </div>
                    <div class="text-muted" style="text-align: center; margin-top: 20px; font-size: 0.9rem;" id="mock-no-alerts">
                        No active emergencies.
                    </div>
                </div>

                <!-- Mission & AI Event Logs -->
                <div class="glass-panel" style="flex: 1; display: flex; flex-direction: column;">
                    <h3 style="margin-bottom: var(--spacing-md); font-size: 1rem;">System Logs</h3>
                    <div class="flex-col" style="gap: 0; overflow-y: auto; flex: 1;">
                        <div class="log-entry">[14:32:01] SYS: Database sync OK.</div>
                        <div class="log-entry warning">[14:35:12] AEGIS-02: Wind speed at caution threshold (18mph).</div>
                        <div class="log-entry">[14:40:05] AEGIS-01: User requested tracking.</div>
                        <div class="log-entry list">[14:40:10] AEGIS-01: Take-off nominal. Target lock acquired.</div>
                        <div class="log-entry warning">[14:42:22] AEGIS-01: AI Vision - Unrecognized entity entering safe radius.</div>
                        <div class="log-entry">[14:42:25] AEGIS-01: Entity exited radius. Resuming standard track.</div>
                    </div>
                </div>
            </div>

        </div>
    `;

    // Secret double-click header to trigger mock emergency
    const headerTrigger = container.querySelector('.text-danger');
    const alertBox = container.querySelector('#mock-alert-box');
    const textNoAlerts = container.querySelector('#mock-no-alerts');

    headerTrigger.addEventListener('dblclick', () => {
        alertBox.classList.remove('hidden');
        textNoAlerts.style.display = 'none';
        
        // Change global border to signify alert
        container.querySelector('.admin-dashboard').style.boxShadow = 'inset 0 0 50px rgba(255, 51, 102, 0.2)';
    });

    const ackBtn = alertBox.querySelector('button');
    ackBtn.addEventListener('click', () => {
        alert('Emergency acknowledged. Ground team dispatched to location.');
        alertBox.classList.add('hidden');
        textNoAlerts.style.display = 'block';
        container.querySelector('.admin-dashboard').style.boxShadow = 'none';
    });

    // Cross-view event listener: Catches the SOS emitted from the user application
    window.addEventListener('aegis-sos-triggered', () => {
        // Trigger the red UI alerts
        alertBox.classList.remove('hidden');
        textNoAlerts.style.display = 'none';
        container.querySelector('.admin-dashboard').style.boxShadow = 'inset 0 0 50px rgba(255, 51, 102, 0.2)';

        // Add to System Logs
        const logContainer = container.querySelectorAll('.flex-col')[1]; // Second flex-col is logs block
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        const newLog = document.createElement('div');
        newLog.className = 'log-entry warning';
        newLog.style.color = '#ff3366';
        newLog.innerHTML = `[${timeStr}] AEGIS-01: CRITICAL - EMERGENCY SOS ACTIVATED. Initiating Priority Override.`;
        
        // Push it cleanly to the front of the log list
        logContainer.prepend(newLog);
    });

        let activeAdminMap = null;
        const fleetMarkers = [];

        // Initialize Mapbox Admin Map
        setTimeout(() => {
            mapboxgl.accessToken = 'pk.eyJ1IjoiY2hhcmFua2FrdWxhIiwiYSI6ImNtbWd4aG9kNjBhNjQycHB0ZGc3ZHVtdjcifQ.hWbgSljS6hkSlh56nRuOrA';
            activeAdminMap = new mapboxgl.Map({
                container: 'admin-map',
                style: 'mapbox://styles/mapbox/dark-v11', // Dark style
                center: [-105.2705, 40.0150], // Center on Boulder
                zoom: 13,
                pitch: 30 // 3D tilt
            });

            // Setup 3D Buildings Layer
            activeAdminMap.on('style.load', () => {
                const layers = activeAdminMap.getStyle().layers;
                let labelLayerId;
                for (let i = 0; i < layers.length; i++) {
                    if (layers[i].type === 'symbol' && layers[i].layout['text-field']) {
                        labelLayerId = layers[i].id;
                        break;
                    }
                }
                 
                activeAdminMap.addLayer({
                    'id': 'add-3d-buildings',
                    'source': 'composite',
                    'source-layer': 'building',
                    'filter': ['==', 'extrude', 'true'],
                    'type': 'fill-extrusion',
                    'minzoom': 14,
                    'paint': {
                        'fill-extrusion-color': '#1f2937', 
                        'fill-extrusion-height': ['get', 'height'],
                        'fill-extrusion-base': ['get', 'min_height'],
                        'fill-extrusion-opacity': 0.9
                    }
                }, labelLayerId);
            });

            // Iterate and add all drone markers
            fleetDrones.forEach((d, idx) => {
                const el = document.createElement('div');
                el.className = d.status.includes('Charging') ? 'custom-marker-charging' : 'custom-marker-drone';
                
                // Add click listener directly to map marker element
                el.addEventListener('click', (e) => {
                    e.stopPropagation();
                    selectDrone(idx);
                });

                const marker = new mapboxgl.Marker({ element: el })
                    .setLngLat([d.lng, d.lat])
                    .setPopup(new mapboxgl.Popup({ closeButton: false }).setHTML(`<b>${d.id}</b><br>${d.status}`))
                    .addTo(activeAdminMap);
                    
                fleetMarkers.push(marker);
            });
            
            // Open the first popup by default
            if(fleetMarkers.length > 0) fleetMarkers[0].togglePopup();

            // Add Navigation controls
            activeAdminMap.addControl(new mapboxgl.NavigationControl(), 'bottom-right');
        }, 100);

        // UI State Interaction Logic
        const listItems = container.querySelectorAll('.drone-list-item');
        const activeFeedMedia = container.querySelector('#active-feed-media');
        const activeFeedOverlay = container.querySelector('#active-feed-overlay');
        const activeAiLabel = container.querySelector('#active-ai-label');
        const activeTelemetry = container.querySelector('#active-telemetry');

        const overviewBtn = container.querySelector('#btn-fleet-overview');
        const adminDashboard = container.querySelector('.admin-dashboard');

        function selectOverview() {
            // Unselect all drones
            listItems.forEach(li => li.classList.remove('selected'));
            overviewBtn.classList.add('selected');
            
            // Toggle view mode classes
            adminDashboard.classList.remove('drone-mode');
            adminDashboard.classList.add('overview-mode');
            
            fleetMarkers.forEach(m => { if(m.getPopup().isOpen()) m.togglePopup(); });
            
            // Re-center map to see all drones
            if (activeAdminMap) {
                activeAdminMap.flyTo({ center: [-105.2705, 40.0150], zoom: 13, pitch: 30, essential: true });
            }
        }

        function selectDrone(index) {
            overviewBtn.classList.remove('selected');
            
            // Toggle view mode classes
            adminDashboard.classList.remove('overview-mode');
            adminDashboard.classList.add('drone-mode');

            // Unselect all
            listItems.forEach(li => li.classList.remove('selected'));
            fleetMarkers.forEach(m => { if(m.getPopup().isOpen()) m.togglePopup(); });
            
            // Select matching
            const targetItem = container.querySelector(`.drone-list-item[data-index="${index}"]`);
            if (targetItem) targetItem.classList.add('selected');
            
            const d = fleetDrones[index];
            
            // Update Dashboard UI Variables
            activeFeedMedia.style.background = `url('${d.vid}') no-repeat center center/cover`;
            activeFeedOverlay.textContent = `${d.id} : ${d.status.toUpperCase()} : REC`;
            activeAiLabel.textContent = d.ai;
            activeTelemetry.innerHTML = d.telemetry;
            
            // Re-trigger animation
            activeFeedMedia.classList.remove('ken-burns');
            void activeFeedMedia.offsetWidth; // trigger reflow
            activeFeedMedia.classList.add('ken-burns');
            
            // Fly map and open popup
            if (activeAdminMap) {
                activeAdminMap.flyTo({ center: [d.lng, d.lat], zoom: 16, essential: true });
                fleetMarkers[index].togglePopup();
            }
        }

        // Attach click listeners to sidebar list
        overviewBtn.addEventListener('click', () => selectOverview());

        listItems.forEach(item => {
            if (item.id === 'btn-fleet-overview') return;
            item.addEventListener('click', () => {
                const idx = parseInt(item.getAttribute('data-index'));
                selectDrone(idx);
            });
        });

        // Trigger resize event to fix map render bugs when toggling sections
        overviewBtn.addEventListener('click', () => { setTimeout(() => window.dispatchEvent(new Event('resize')), 50); });
        listItems.forEach(item => {
            item.addEventListener('click', () => { setTimeout(() => window.dispatchEvent(new Event('resize')), 50); });
        });
}
