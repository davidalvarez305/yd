class AudioPlayerInterface {
    play(src) {
        throw new Error("play(src) must be implemented.");
    }

    pause(src) {
        throw new Error("pause(src) must be implemented.");
    }

    stop(src) {
        throw new Error("stop(src) must be implemented.");
    }

    setPlaybackRate(src, rate) {
        throw new Error("setPlaybackRate(src, rate) must be implemented.");
    }
}

export class DefaultAudioPlayer extends AudioPlayerInterface {
    constructor() {
        super();
        this.audioMap = new Map();
    }

    getAudioElement(src) {
        if (!this.audioMap.has(src)) {
            const audio = new Audio(src);
            audio.preload = "auto";
            this.audioMap.set(src, audio);
        }
        return this.audioMap.get(src);
    }

    play(src) {
        this.getAudioElement(src).play();
    }

    pause(src) {
        this.getAudioElement(src).pause();
    }

    stop(src) {
        const audio = this.getAudioElement(src);
        audio.pause();
        audio.currentTime = 0;
    }

    setPlaybackRate(src, rate) {
        this.getAudioElement(src).playbackRate = rate;
    }
}

export class HowlerAudioPlayer extends AudioPlayerInterface {
    constructor() {
        super();
        this.howlMap = new Map();
    }

    getHowl(src) {
        if (!this.howlMap.has(src)) {
            const howl = new Howl({
                src: [src],
                html5: true
            });
            this.howlMap.set(src, howl);
        }
        return this.howlMap.get(src);
    }

    play(src) {
        this.getHowl(src).play();
    }

    pause(src) {
        this.getHowl(src).pause();
    }

    stop(src) {
        this.getHowl(src).stop();
    }

    setPlaybackRate(src, rate) {
        this.getHowl(src).rate(rate);
    }
}

export function createAudioPlayerFactory() {
    if (typeof window.Howl === 'function') {
        return new HowlerAudioPlayer();
    }

    return new DefaultAudioPlayer();
}