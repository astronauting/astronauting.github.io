/* Restore the theme before the body paints; no third-party dependency. */
(function () {
    'use strict';
    var root = document.documentElement;
    var system = window.matchMedia('(prefers-color-scheme: dark)');
    var preference = null;
    var button;

    function readPreference() {
        try {
            var value = localStorage.getItem('blog-theme');
            return value === 'light' || value === 'dark' ? value : null;
        } catch (error) {
            // Storage may be blocked; the switch still works for this page.
            return null;
        }
    }

    function render() {
        var dark = (preference || (system.matches ? 'dark' : 'light')) === 'dark';
        root.dataset.theme = dark ? 'dark' : 'light';
        if (button) {
            button.textContent = dark ? '\u2600 日间模式' : '\u263e 夜间模式';
            button.setAttribute('aria-pressed', String(dark));
            button.title = dark ? '切换到日间模式' : '切换到夜间模式';
        }
    }

    preference = readPreference();
    render();
    system.addEventListener('change', render);
    window.addEventListener('storage', function (event) {
        if (event.key === 'blog-theme' || event.key === null) {
            preference = readPreference();
            render();
        }
    });
    document.addEventListener('DOMContentLoaded', function () {
        button = document.createElement('button');
        button.id = 'theme-toggle';
        button.type = 'button';
        button.setAttribute('aria-label', '夜间模式');
        button.addEventListener('click', function () {
            preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
            try {
                localStorage.setItem('blog-theme', preference);
            } catch (error) {
                // Keep the in-memory preference if persistent storage is blocked.
            }
            render();
        });
        document.body.appendChild(button);
        render();
    });
}());
