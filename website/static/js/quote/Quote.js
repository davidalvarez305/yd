import { createServiceFactory, Service } from "./Service.js";

export default class Quote {
    constructor() {
        this.services = [];
        this.hours = null;
        this.guests = null;

        this._editableFields = ['unit', 'price'];
        this._cachedFields = new Map();

        this._editableFields.forEach(id => {
            const el = document.getElementById(id);
            this._cachedFields.set(id, el);
        });
    }

    _scanWebPage() {
        const hours = document.getElementById('hours');
        if (hours) {
            this.hours = hours;
            hours.addEventListener('change', event => this.handleChangeHours(event.target.value));
        }

        const guests = document.getElementById('guests');
        if (guests) {
            this.guests = guests;
            guests.addEventListener('change', event => this.handleChangeGuests(event.target.value));
        }

        const service = document.getElementById('service');
        if (service) {
            service.addEventListener('change', event => this.handleChangeService(event.target));
        }
    }

    handleChangeHours(value) {
        if (value === this.hours?.value) return;
        // Adjust prices based on hours
    }

    handleChangeGuests(value) {
        if (value === this.guests?.value) return;
        // Adjust price based on guests
    }

    handleChangeService(input) {
        const index = input.selectedIndex;
        if (!index) return;

        const option = input.options[index];
        const service = createServiceFactory({ ...option.dataset });

        for (const [key, field] of Object.entries(this._cachedFields)) {
            const value = service[key];
            if (value) field.value = String(value);
        }
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const quote = new Quote();

    quote._scanWebPage();
});