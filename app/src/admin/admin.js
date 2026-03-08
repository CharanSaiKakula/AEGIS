import './admin.css';

export function renderAdminView(container) {
    container.innerHTML = `
        <div class="admin-dashboard">
            
            <!-- Left Sidebar: Fleet & Controls -->
            <div class="admin-sidebar-left">
                <!-- Fleet Overview -->
                <div class="glass-panel" style="flex: 1; display: flex; flex-direction: column;">
                    <div class="space-between flex-row" style="margin-bottom: var(--spacing-md); border-bottom: 1px solid var(--border-subtle); padding-bottom: 8px;">
                        <h2 class="text-accent" style="margin-bottom: 0;">Fleet Status</h2>
                        <span class="text-muted" style="font-size: 0.8rem;">3 Active / 5 Total</span>
                    </div>
                    
                    <div class="flex-col" style="gap: 8px; overflow-y: auto;">
                        <div class="drone-list-item selected">
                            <div>
                                <div style="font-weight: bold;">Sentry-01</div>
                                <div class="text-muted" style="font-size: 0.75rem;">Status: Active Tracking</div>
                            </div>
                            <div style="text-align: right;">
                                <span class="text-success" style="font-size: 0.8rem;">82%</span>
                                <div class="battery-bar"><div class="battery-fill" style="width: 82%;"></div></div>
                            </div>
                        </div>

                        <div class="drone-list-item">
                            <div>
                                <div style="font-weight: bold;">Sentry-02</div>
                                <div class="text-muted" style="font-size: 0.75rem;">Status: Hover / Idle</div>
                            </div>
                            <div style="text-align: right;">
                                <span class="text-success" style="font-size: 0.8rem;">95%</span>
                                <div class="battery-bar"><div class="battery-fill" style="width: 95%;"></div></div>
                            </div>
                        </div>

                        <div class="drone-list-item" style="opacity: 0.6;">
                            <div>
                                <div style="font-weight: bold;">Sentry-03</div>
                                <div class="text-danger" style="font-size: 0.75rem;">Status: Charging at Base</div>
                            </div>
                            <div style="text-align: right;">
                                <span class="text-danger" style="font-size: 0.8rem;">14%</span>
                                <div class="battery-bar"><div class="battery-fill critical" style="width: 14%;"></div></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Manual Override Controls -->
                <div class="glass-panel">
                    <h3 style="margin-bottom: var(--spacing-md); font-size: 1rem;">Manual Controls <span class="text-muted">(Sentry-01)</span></h3>
                    <div class="control-grid">
                        <button class="btn">Return Base</button>
                        <button class="btn">Hover in Place</button>
                        <button class="btn">Alt +10ft</button>
                        <button class="btn">Alt -10ft</button>
                        <button class="btn btn-danger" style="grid-column: span 2;">Trigger Siren</button>
                    </div>
                </div>
            </div>

            <!-- Middle Main Area: Video & Global Map -->
            <div class="admin-main-area">
                
                <!-- KPI Header -->
                <div class="glass-panel flex-row space-between" style="padding: 10px 20px;">
                    <div>
                        <div class="text-muted" style="font-size: 0.8rem;">Global System Status</div>
                        <div class="text-success" style="font-weight: bold;">Online & Stable</div>
                    </div>
                    <div>
                        <div class="text-muted" style="font-size: 0.8rem;">Active Missions</div>
                        <div style="font-weight: bold;">1</div>
                    </div>
                    <div>
                        <div class="text-muted" style="font-size: 0.8rem;">Total AI Events (24h)</div>
                        <div style="font-weight: bold;">142</div>
                    </div>
                </div>

                <!-- Live Monitoring Video Grid -->
                <div class="video-grid">
                    <!-- Feed 1 (Active) -->
                    <div class="video-feed" style="border-color: var(--accent-cyan); box-shadow: 0 0 15px rgba(0, 240, 255, 0.1);">
                        <div class="video-overlay">SENTRY-01 : TRACKING ACTIVE : REC</div>
                        
                        <!-- Mock AI Box Outline -->
                        <div class="ai-box animate-pulse" style="width: 80px; height: 160px; top: 30%; left: 40%;">
                            <div class="ai-label">PERSON [98%]</div>
                        </div>

                        <div style="color: rgba(255,255,255,0.2); font-family: monospace;">[No Physical Camera Attached]</div>
                        
                        <!-- Telemetry Overlay Bottom right -->
                        <div style="position: absolute; bottom: 10px; right: 10px; text-align: right; font-family: monospace; font-size: 0.8rem; color: var(--accent-cyan); background: rgba(0,0,0,0.5); padding: 4px;">
                            ALT: 45ft<br>
                            SPD: 12mph<br>
                            GPS: LOCK
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
                        <strong>User Panic Button Triggered</strong><br>
                        Drone: Sentry-01<br>
                        Loc: North Quad Path<br>
                        <button class="btn btn-danger w-full" style="margin-top: 8px; padding: 4px;">Acknowledge</button>
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
                        <div class="log-entry warning">[14:35:12] Sentry-02: Wind speed at caution threshold (18mph).</div>
                        <div class="log-entry">[14:40:05] Sentry-01: User requested tracking.</div>
                        <div class="log-entry list">[14:40:10] Sentry-01: Take-off nominal. Target lock acquired.</div>
                        <div class="log-entry warning">[14:42:22] Sentry-01: AI Vision - Unrecognized entity entering safe radius.</div>
                        <div class="log-entry">[14:42:25] Sentry-01: Entity exited radius. Resuming standard track.</div>
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
        alertBox.classList.add('hidden');
        textNoAlerts.style.display = 'block';
        container.querySelector('.admin-dashboard').style.boxShadow = 'none';
    });

    // Initialize Mapbox Admin Map
    setTimeout(() => {
        mapboxgl.accessToken = 'pk.eyJ1IjoiY2hhcmFua2FrdWxhIiwiYSI6ImNtbWd4aG9kNjBhNjQycHB0ZGc3ZHVtdjcifQ.hWbgSljS6hkSlh56nRuOrA';
        const adminMap = new mapboxgl.Map({
            container: 'admin-map',
            style: 'mapbox://styles/mapbox/dark-v11', // Dark style
            center: [-105.2705, 40.0150], // Center on Boulder
            zoom: 13,
            pitch: 30 // Slight 3D tilt
        });

        // Setup 3D Buildings Layer
        adminMap.on('style.load', () => {
            const layers = adminMap.getStyle().layers;
            let labelLayerId;
            for (let i = 0; i < layers.length; i++) {
                if (layers[i].type === 'symbol' && layers[i].layout['text-field']) {
                    labelLayerId = layers[i].id;
                    break;
                }
            }
             
            adminMap.addLayer({
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

        // Add Mock Fleet Markers (Drones) with Custom HTML
        
        // Active Drone (Sentry-01) - Cyan
        const el1 = document.createElement('div');
        el1.className = 'custom-marker-drone';
        new mapboxgl.Marker({ element: el1 })
            .setLngLat([-105.2805, 40.0160])
            .setPopup(new mapboxgl.Popup().setHTML("<b>Sentry-01</b><br>Active Tracking"))
            .addTo(adminMap);
        
        // Idle Drone (Sentry-02) - Cyan
        const el2 = document.createElement('div');
        el2.className = 'custom-marker-drone';
        new mapboxgl.Marker({ element: el2 })
            .setLngLat([-105.2605, 40.0110])
            .setPopup(new mapboxgl.Popup().setHTML("<b>Sentry-02</b><br>Idle"))
            .addTo(adminMap);
            
        // Charging Drone (Sentry-03) - Red
        const el3 = document.createElement('div');
        el3.className = 'custom-marker-charging';
        new mapboxgl.Marker({ element: el3 })
            .setLngLat([-105.2715, 40.0180])
            .setPopup(new mapboxgl.Popup().setHTML("<b>Sentry-03</b><br>Charging"))
            .addTo(adminMap);

        // Add Navigation controls
        adminMap.addControl(new mapboxgl.NavigationControl(), 'bottom-right');
    }, 100);
}
