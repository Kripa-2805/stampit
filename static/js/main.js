const themeToggle = document.getElementById('theme-toggle');
const currentTheme = localStorage.getItem('theme') || 'dark';

// Set initial theme
document.documentElement.setAttribute('data-theme', currentTheme);
updateIcon(currentTheme);

if (themeToggle) themeToggle.addEventListener('click', () => {
    let theme = document.documentElement.getAttribute('data-theme');
    let newTheme = theme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateIcon(newTheme);
});

function updateIcon(theme) {
    if (theme === 'dark') {
        themeToggle.innerHTML = '<i data-lucide="moon"></i>'; // Half-moon for dark
    } else {
        themeToggle.innerHTML = '<i data-lucide="sun"></i>'; // Sun for light
    }
    lucide.createIcons(); // Refresh Lucide icons
}

// Run once on load to ensure icon is correct
updateIcon(currentTheme);

