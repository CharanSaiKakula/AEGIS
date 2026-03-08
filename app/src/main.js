import './style.css';
import { renderLoginView } from './auth/login.js';
import { renderUserView } from './user/user.js';
import { renderAdminView } from './admin/admin.js';

// Base routing/view switching logic
document.addEventListener('DOMContentLoaded', () => {
    
    const loginView = document.getElementById('login-view');
    const userView = document.getElementById('user-view');
    const adminView = document.getElementById('admin-view');
    
    const userProfileControls = document.getElementById('user-profile-controls');
    const loggedInUserSpan = document.getElementById('logged-in-user');
    const btnLogout = document.getElementById('btn-logout');

    function handleLoginSuccess(role) {
        // Hide login view
        loginView.classList.add('hidden');
        userProfileControls.style.display = 'flex';

        if (role === 'admin') {
            loggedInUserSpan.textContent = 'Admin Mode';
            adminView.classList.remove('hidden');
            // If reusing elements, we'd normally clear and re-render here.
            // For this mock, we just unhide the pre-rendered container.
        } else {
            loggedInUserSpan.textContent = 'User: Charan';
            userView.classList.remove('hidden');
        }

        // Force a window resize event to tell Mapbox to recalculate its bounds
        // now that its parent container is no longer display: none
        setTimeout(() => window.dispatchEvent(new Event('resize')), 50);
    }

    function handleLogout() {
        userProfileControls.style.display = 'none';
        userView.classList.add('hidden');
        adminView.classList.add('hidden');
        loginView.classList.remove('hidden');
        
        // Re-render fresh login screen to clear inputs
        renderLoginView(loginView, handleLoginSuccess);
    }

    btnLogout.addEventListener('click', handleLogout);

    // Initialize specific views
    renderLoginView(loginView, handleLoginSuccess);
    renderUserView(userView);
    renderAdminView(adminView);

});
