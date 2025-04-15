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

window.onload = function() {
	var startTime = Date.now();

	window.onbeforeunload = function() {
		var endTime = Date.now();
		var session_duration = (endTime - startTime) / 1000;

		var visit_id = "{{ request.visit_id }}";

		fetch("{% url 'visit_update' %}", {
			method: "POST",
			headers: {
				"X-CSRFToken": "{{ csrf_token }}",
			},
			body: new FormData({ visit_id, session_duration })
		});
	};
};