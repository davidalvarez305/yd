import { createServiceFactory, Service } from "./Service.js";

export default class Quote {
    constructor() {
        this.services = [];
        this.hours = null;
        this.guests = null;

        this._scan();
    }

    addService(service) {
        this.services.push(service);
    }

    _scan() {
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

    handleChangeService(element) {
        let id = element.dataset.serviceId;

        let service = createServiceFactory({ ...element.dataset });

        this.addService(service);
    }
}