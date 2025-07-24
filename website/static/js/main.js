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