import { createServiceOptionFactory } from "./Service.js";
import { createQuoteServiceFactory } from "./QuoteService.js";

const FORM_MAPPER = {
    units: {
        html: 'unit',
        model: 'units',
    },
    price: {
        html: 'price',
        model: 'price_per_units',
    },
    service: {
        html: 'service',
        model: 'service',
    }
};

export default class Quote {
    constructor() {
        this.quoteServices = [];
        this.state = new Map();
        this._variableFormFields = new Map();

        ['units', 'price'].forEach(id => {
            const el = document.getElementById(id);
            if (el) this._variableFormFields.set(id, el);
        });
    }

    _scanWebPage() {
        ['hours', 'guests'].forEach(key => {
            const el = document.getElementById(key);

            if (!el) return;

            this.state.set(key, el);
            el.addEventListener('change', () => this._handleFieldChange(key, el.value));
        });

        const service = document.getElementById('service');

        if (service) service.addEventListener('change', event => this._handleChangeService(event.target));
    }

    _handleFieldChange(key, value) {
        this.state.set(key, value);

        this.quoteServices.forEach(service => {
            let guests = this.state.get('guests')?.value;
            let hours = this.state.get('hours')?.value;

            const { units, price } = service.calculate(guests, hours);
            let quoteService = createQuoteServiceFactory({ 
                service: service.id,
                quote: quote.id,
                units: units,
                price: price,
             });
            this.quoteServices.push(quoteService);
            this._fillFormFields({ units, price });
        });
    }

    _handleChangeService(input) {
        const index = input.selectedIndex;
        if (!index) return;

        const option = input.options[index];

        let guests = this.state.get('guests')?.value;
        let hours = this.state.get('hours')?.value;
        const service = createServiceOptionFactory({ ...option.dataset });
        const { units, price } = service.calculate(guests, hours);
        let quoteService = createQuoteServiceFactory({ 
            service: service.id,
            quote: quote.id,
            units: units,
            price: price,
            });
        this.quoteServices.push(quoteService);
        this._fillFormFields({ units, price });
    }

    _fillFormFields(data) {
        for (const [key, field] of this._variableFormFields.entries()) {
            if (data[key]) field.value = String(value);
        }
    }

    _serializeService(service) {
        const obj = {};

        for (const [key, mapping] of Object.entries(FORM_MAPPER)) {
            const field = mapping.model;
            const value = service[key];

            if (value) obj[field] = value;
        }

        return obj;
    }

    getData() {
        const data = new FormData();

        for (const [key, input] of this.state.entries()) {
            if (input.value) data.set(key, input.value);
        }

        const serializedServices = this.quoteServices.map(service => this._serializeService(service));
        data.set('quote_services', JSON.stringify(serializedServices));

        return data;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const quote = new Quote();
    quote._scanWebPage();
});
