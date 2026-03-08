import './login.css';

export function renderLoginView(container, onLoginSuccess) {
    container.innerHTML = `
        <div class="login-container">
            <div class="glass-panel login-panel">
                <div class="login-header" style="text-align: center;">
                    <div class="brand">
                        <span class="text-main" style="font-family: 'Outfit', sans-serif; letter-spacing: 2px;">RALPHLY</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #e0e0e0; margin-top: 5px; font-weight: 500; letter-spacing: 0.5px;">Your friendly campus drone escort</div>
                </div>

                <div class="drone-animation-track">
                    <img class="ralphie-drone" src="/assets/ralphie-drone.png" alt="Ralphie Drone" />
                </div>


                <div id="login-error" class="error-message hidden">
                    Invalid credentials. Please try again.
                </div>

                <form id="login-form" class="login-form">
                    <div class="form-group">
                        <label>Username</label>
                        <input type="text" id="username-input" class="form-input" required autocomplete="off">
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <input type="password" id="password-input" class="form-input" required autocomplete="off">
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-full" style="margin-top: 8px;">Login</button>
                </form>
                
                <div style="text-align: center; margin-top: 5px; margin-bottom: 5px; font-size: 0.8rem; color: rgba(255, 255, 255, 0.5); letter-spacing: 0.5px;">
                    Serving CU Boulder Students
                </div>
            </div>
        </div>
    `;

    const form = container.querySelector('#login-form');
    const errorMsg = container.querySelector('#login-error');
    const userIn = container.querySelector('#username-input');
    const passIn = container.querySelector('#password-input');

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const username = userIn.value.trim().toLowerCase();
        const password = passIn.value.trim();

        // Simple hardcoded mock credentials
        if (username === 'admin' && password === 'admin@fly') {
            errorMsg.classList.add('hidden');
            onLoginSuccess('admin');
        } else if (username === 'charan' && password === 'student123') {
            errorMsg.classList.add('hidden');
            onLoginSuccess('user');
        } else {
            errorMsg.classList.remove('hidden');
            passIn.value = ''; // clear password
        }
    });

    // Auto-focus username on load
    setTimeout(() => {
        userIn.focus();
    }, 100);
}
