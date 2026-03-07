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
                        <input type="text" class="form-input" value="University Library, North Entrance" readonly>
                    </div>
                    <div class="form-group" style="margin-top: 12px;">
                        <label>Destination</label>
                        <input type="text" class="form-input" placeholder="e.g. Dormitory C, East Wing" id="dest-input">
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
                <div class="viewport-container" id="user-viewport">
                    <div class="mock-map-bg"></div>
                    
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
}
