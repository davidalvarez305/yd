// service type = hourly, general, food, rental, alcohol, etc...
// unit type = per person, ratio, hourly, etc...
const BASELINE_HOURS = 4;

export default class Service {
    constructor(type, unit, id, price, ratio) {
        this.type = type;
        this.unit = unit;
        this.id = id;
        this.price = price;
        this.ratio = ratio;
    }

    calculate(guests, hours) {
        switch (this.type) {
            case 'PER_PERSON':
                return this.price * guests * (hours / BASELINE_HOURS);
            case 'HOURLY':
                let price = this.price * hours;
                let ratioAdjustment = Math.ceil(guests / this.ratio); // round up to nearest int
                return price * ratioAdjustment;
        }
    }
}