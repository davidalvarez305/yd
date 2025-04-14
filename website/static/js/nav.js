const highlightedPageClass = "group flex items-center gap-2 rounded-lg border border-primary-100 bg-primary-50 px-2.5 text-sm font-medium text-gray-900 dark:border-transparent dark:bg-gray-700/75 dark:text-white";
const normalPageClass = "group flex items-center gap-2 rounded-lg border border-transparent px-2.5 text-sm font-medium text-gray-800 hover:bg-primary-50 hover:text-gray-900 active:border-primary-100 dark:text-gray-200 dark:hover:bg-gray-700/75 dark:hover:text-white dark:active:border-gray-600";
const currentPage = window.location.pathname;
const navButtons = document.querySelectorAll(".navButtons");

navButtons.forEach(button => {
    const pageName = button.getAttribute('href');

    if (currentPage === pageName) {
        button.className = highlightedPageClass;
        return;
    }

    button.className = normalPageClass;
});

const toggleMobileSidebar = document.querySelectorAll('.toggleMobileSidebar');
let isOpen = false;
const mobileClosed = '-translate-x-full';
const mobileOpened = 'translate-x-0';

toggleMobileSidebar.forEach(el => {
    el.addEventListener('click', () => {
        isOpen = !isOpen;
        const sidebar = document.getElementById('page-sidebar');

        if (isOpen) {
            sidebar.classList.remove(mobileClosed);
            sidebar.classList.add(mobileOpened);
        } else {
            sidebar.classList.remove(mobileOpened);
            sidebar.classList.add(mobileClosed);
        }
    });
});