import { createServiceFactory, Service } from "./Service.js";

export default class Quote {
    constructor() {
        this.services = [];
        this.hours = null;
        this.guests = null;
    }

    addService(service) {
        this.services.push(service);
    }

    _scanWebPage() {
        const hours = document.getElementById('hours');
        if (hours) this.hours = hours;
        
        hours.addEventListener('change', event => this.handleChangeHours(event.target.value));

        const guests = document.getElementById('guests');
        if (guests) this.guests = guests;
        
        guests.addEventListener('change', event => this.handleChangeGuests(event.target.value));

        const service = document.getElementById('service');
        service.addEventListener('change', event => this.handleChangeService(event.target));
    }

    handleChangeHours(value) {
        if (value === this.hours) return;

        // Adjust prices based on hours
    }

    handleChangeGuests(value) {
        if (value === this.guests) return;

        // Adjust price based on guests
    }

    handleChangeService(input) {
        let index = input.selectedIndex;

        if (!index) return;

        const option = input.options[index];

        const service = createServiceFactory({ ...option.dataset });

        this.addService(service);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const quote = new Quote();
    quote._scanWebPage();
});