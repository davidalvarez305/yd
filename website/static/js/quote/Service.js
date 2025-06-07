import { QuoteService } from "./QuoteService.js";
const BASELINE_HOURS = 4;

function assert(value, name) {
    if (value === null || value === undefined) {
        throw new Error(`${name} cannot be null or undefined.`);
    }
}

export function createServiceOptionFactory({
    service,
    unit,
    id,
    price = null,
    ratio = null,
}) {
    assert(service, 'Service type');
    assert(unit, 'Unit type');
    assert(id, 'Service ID');

    return new ServiceOption(service, unit, id, price, ratio);
}

export class ServiceOption {
    constructor(service, unit, id, price, ratio) {
        this.service = service;
        this.unit = unit;
        this.id = id;
        this.price = price;
        this.ratio = ratio;
    }

    calculate(guests, hours) {
        switch (this.unit) {
            case 'Per Person':
                let units = guests;
                let price = this.price;

                if (this.service === "Add On") price *= (hours / BASELINE_HOURS);

                return { units, price };
            case 'Hourly': {
                let units = this.ratio ? Math.ceil(guests / this.ratio) * hours : hours;
                let price = this.price;
                return { units, price };
            }
            default:
                return {};
        }
    }
}