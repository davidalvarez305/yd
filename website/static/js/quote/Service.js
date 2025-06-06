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
            case 'PER_PERSON':
                return this.price * guests * (hours / BASELINE_HOURS);
            case 'HOURLY':
                let price = this.price * hours;
                let units = Math.ceil(guests / this.ratio);
                if (this.ratio) price *= Math.ceil(guests / this.ratio);
                return { units, price };
            case 'HOURLY':
                this.price = this.price * hours;
                this.units = Math.ceil(guests / this.ratio);
                return price * ratioAdjustment;
            case 'FIXED':
                return this.price;
            case 'AD_HOC':
                return this.price;
        }
    }
}