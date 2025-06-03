
export default class Quote {
    constructor() {
        this.services = [];
        this.hours = null;
        this.guests = null;
    }

    addService(service) {
        this.services.push(service);
    }

    scan() {
        let hours = document.getElementById('hours');
        if (hours) this.hours = hours;
        
        hours.addEventListener('change', event => this.handleChangeHours(event.target.value));

        let guests = document.getElementById('guests');
        if (guests) this.guests = guests;
        
        guests.addEventListener('change', event => this.handleChangeGuests(event.target.value));
    }

    handleChangeHours(value) {
        if (value === this.hours) return;

        // Adjust prices based on hours
    }

    handleChangeGuests(value) {
        if (value === this.guests) return;

        // Adjust price based on guests
    }
}