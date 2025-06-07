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
        this.quoteId = this._extractQuoteIdFromUrl();
        this.quoteServices = [];
        this.state = new Map();
        this._variableFormFields = new Map();

        this._initFormFields();
    }

    _initFormFields() {
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
        if (service) {
            service.addEventListener('change', event => this._handleChangeService(event.target));
        }

        let services = JSON.parse(document.getElementById('quoteServices').textContent);
        
        services.forEach(service => {
            this.quoteServices.push(createQuoteServiceFactory({
                    service: service.service_id,
                    quote: service.quote_id,
                    price: service.price_per_unit,
                    units: service.units,
                    id: service.quote_service_id,
                })
            );
        });

        console.log(this.quoteServices);
    }

    _extractQuoteIdFromUrl() {
        const match = window.location.pathname.match(/\/crm\/quote\/(\d+)/);
        return match?.[1] ?? null;
    }

    _handleFieldChange(key, value) {
        this.state.set(key, value);

        const guests = this.state.get('guests')?.value;
        const hours = this.state.get('hours')?.value;

        this.quoteServices.forEach(service => {
            this._processServiceCalculation(service, guests, hours);
        });
    }

    _handleChangeService(input) {
        const option = input.options[input.selectedIndex];
        if (!option?.dataset?.id) return;

        const guests = this.state.get('guests')?.value;
        const hours = this.state.get('hours')?.value;

        const service = createServiceOptionFactory({ ...option.dataset });
        this.quoteServices.push(service);
        this._processServiceCalculation(service, guests, hours);
    }

    _processServiceCalculation(service, guests, hours) {
        const { units, price } = service.calculate(guests, hours);

        const quoteService = createQuoteServiceFactory({
            service: service.id,
            quote: this.quoteId,
            units,
            price
        });

        this.quoteServices.push(quoteService);
        this._fillFormFields({ units, price });
    }

    _fillFormFields(data) {
        for (const [key, field] of this._variableFormFields.entries()) {
            if (data[key]) field.value = String(data[key]);
        }
    }

    _serializeService(service) {
        const obj = {};

        for (const [key, { model }] of Object.entries(FORM_MAPPER)) {
            const value = service[key];
            if (value) obj[model] = value;
        }

        return obj;
    }

    getData() {
        const data = new FormData();

        for (const [key, input] of this.state.entries()) {
            if (input.value) data.set(key, input.value);
        }

        const serializedServices = this.quoteServices.map(s => this._serializeService(s));
        data.set('quote_services', JSON.stringify(serializedServices));

        return data;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const quote = new Quote();
    quote._scanWebPage();
});
