/**
 * NearestGrocery — Theme System
 * Handles light/dark theme toggle with localStorage persistence
 */
(function () {
    'use strict';

    const THEME_KEY = 'ng-theme';
    const DARK = 'dark';
    const LIGHT = 'light';

    // Apply saved theme immediately (before DOM paint) to prevent flash
    function applySavedTheme() {
        const saved = localStorage.getItem(THEME_KEY) || LIGHT;
        document.documentElement.setAttribute('data-theme', saved);
    }

    applySavedTheme();

    // Toggle theme and persist
    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-theme') || LIGHT;
        const next = current === DARK ? LIGHT : DARK;
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem(THEME_KEY, next);
        updateToggleIcons(next);
    }

    // Update all toggle buttons on the page
    function updateToggleIcons(theme) {
        const btns = document.querySelectorAll('.theme-toggle-btn');
        btns.forEach(btn => {
            const sunIcon  = btn.querySelector('.icon-sun');
            const moonIcon = btn.querySelector('.icon-moon');
            if (sunIcon && moonIcon) {
                sunIcon.style.display  = theme === DARK  ? 'block' : 'none';
                moonIcon.style.display = theme === LIGHT ? 'block' : 'none';
            }
            btn.setAttribute('aria-label', theme === DARK ? 'Switch to Light Mode' : 'Switch to Dark Mode');
            btn.title = theme === DARK ? 'Switch to Light Mode' : 'Switch to Dark Mode';
        });
    }

    // Wire up buttons after DOM is ready
    document.addEventListener('DOMContentLoaded', function () {
        const currentTheme = document.documentElement.getAttribute('data-theme') || LIGHT;
        updateToggleIcons(currentTheme);

        document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
            btn.addEventListener('click', toggleTheme);
        });
    });

    // Expose globally if needed
    window.ngTheme = { toggle: toggleTheme };
})();
