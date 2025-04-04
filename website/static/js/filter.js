const clearButtons = document.querySelectorAll('.clearButton');

clearButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        window.location.href = window.location.pathname;
    });
});