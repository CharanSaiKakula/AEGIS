import './login.css';

export function renderLoginView(container, onLoginSuccess) {
    container.innerHTML = `
        <div class="login-container">
            <div class="glass-panel login-panel">
                <div class="login-header">
                    <div class="brand">
                        <span class="text-main" style="font-family: 'Outfit', sans-serif; letter-spacing: 2px;">RALPHLY</span>
                    </div>
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
        if (username === 'admin' && password === 'sentry_command') {
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
