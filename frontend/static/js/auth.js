// Authentication state management
document.addEventListener('DOMContentLoaded', function() {
    const authToken = localStorage.getItem('access_token');
    const userNavSection = document.getElementById('user-nav-section');
    const loginNavSection = document.getElementById('login-nav-section');
    const userProfileName = document.getElementById('user-profile-name');

    function updateNavigation() {
        if (authToken) {
            // User is logged in
            try {
                const user = JSON.parse(localStorage.getItem('user'));
                if (loginNavSection) loginNavSection.classList.add('hidden');
                if (userNavSection) userNavSection.classList.remove('hidden');
                if (userProfileName) userProfileName.textContent = user.username || 'User';
            } catch (error) {
                // Clear invalid user data
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
                window.location.href = '/login';
            }
        } else {
            // User is not logged in
            if (loginNavSection) loginNavSection.classList.remove('hidden');
            if (userNavSection) userNavSection.classList.add('hidden');
        }
    }

    // Handle logout
    window.logout = function() {
        fetch('/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        }).finally(() => {
            // Clear authentication data
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            // Redirect to login
            window.location.href = '/login';
        });
    };

    // Initial navigation update
    updateNavigation();
});