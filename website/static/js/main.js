function preserveQuerystring() {
	if (["crm"].some(link => window.location.pathname.includes(link))) return;

	const links = document.querySelectorAll('a');

	links.forEach(link => {
		link.addEventListener('click', function () {
			const qs = window.location.search;
			if (qs.length > 0) {
				const url = new URL(this.href, window.location.origin);
				url.search = url.search ? `${url.search}&${qs.substring(1)}` : qs;
				this.href = url.toString();
			}
		});
	});
}

document.addEventListener("DOMContentLoaded", () => preserveQuerystring());

// HTMX
function handleSubmissionWorkflow(event, isLoading) {
	const form = event.target;
	const spinnerSelector = form.getAttribute('data-loading-target');
	const spinner = document.querySelector(spinnerSelector);
	const submitButton = form.querySelector('button[type="submit"]');

	if (!spinnerSelector || !spinner || !submitButton) return;

	isLoading ? spinner.classList.remove('hidden') : spinner.classList.add('hidden');
	isLoading ? spinner.classList.add('animate-spin') : spinner.classList.remove('animate-spin');
	isLoading ? submitButton.disabled = true : submitButton.disabled = false;
};

document.addEventListener('htmx:configRequest', event => handleSubmissionWorkflow(event, true));
document.addEventListener('htmx:afterRequest', event => handleSubmissionWorkflow(event, false));