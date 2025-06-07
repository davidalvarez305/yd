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
            
            if (!el) throw new Error(`Could not find ${key} element.`);

            this.state.set(key, el);
            el.addEventListener('change', () => this._handleFieldChange(key, el.value));
        });

        const service = document.getElementById('service');
        
        if (!service) throw new Error('Could not find service input.');
        
        service.addEventListener('change', event => this._handleChangeService(event.target));

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
            let quoteService = this._processServiceCalculation(service, guests, hours);

            console.log(this.quoteServices);

            service = quoteService;

            console.log(this.quoteServices);
        });

        this._attachQuoteServices();
    }

    _handleChangeService(input) {
        const option = input.options[input.selectedIndex];
        if (!option.dataset.id) throw new Error('Could not find selected option.');

        const guests = this.state.get('guests').value;
        const hours = this.state.get('hours').value;

        const service = createServiceOptionFactory({ ...option.dataset });
        const { units, price_per_unit } = this._processServiceCalculation(service, guests, hours);

        this._fillFormFields({ units, price: price_per_unit });
    }

    _processServiceCalculation(service, guests, hours) {
        const { units, price } = service.calculate(guests, hours);

        const quoteService = createQuoteServiceFactory({
            id: service.id,
            service: service.service,
            quote: this.quoteId,
            units,
            price
        });

        return quoteService;
    }

    _fillFormFields(data) {
        for (const [key, field] of this._variableFormFields.entries()) {
            if (data[key]) field.value = String(data[key]);
        }
    }

    _serializeServices() {
        const obj = {};

        for (const [key, { model }] of Object.entries(FORM_MAPPER)) {
            const value = service[key];
            if (value) obj[model] = value;
        }

        return obj;
    }

    _attachQuoteServices() {
        let input = document.getElementById('quote_services');

        if (!input) throw new Error('quote_services input not found.');

        input.value = JSON.stringify(this.quoteServices);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const quote = new Quote();
    quote._scanWebPage();
});
