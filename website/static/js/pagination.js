const querystring = new URLSearchParams(window.location.search);

function handlePagination() {
    document.querySelectorAll('.pagination-link').forEach(item => {
        item.addEventListener('click', () => {
            const currentPage = parseInt(querystring.get('page_num') || '1');
            const maxPages = parseInt(document.getElementById('maxPages').textContent);
            const direction = item.getAttribute('name');

            if (direction === 'left' && currentPage > 1) querystring.set('page_num', currentPage - 1);
                
            if (direction === 'right' && currentPage < maxPages) querystring.set('page_num', currentPage + 1);

            if (querystring.has('page_num')) updateURL();
        });
    });
}

function updateURL() {
    const { origin, pathname } = window.location;
    const url = new URL(origin + pathname);
    url.search = querystring.toString();
    window.location.replace(url.href);
}

document.addEventListener('DOMContentLoaded', handlePagination);