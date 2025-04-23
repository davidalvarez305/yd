export class AudioMessage {
    constructor(src, audioPlayer) {
        this.src = src;
        this.audioPlayer = audioPlayer;
    }

    play() {
        this.audioPlayer.play(this.src);
    }

    pause() {
        this.audioPlayer.pause(this.src);
    }

    stop() {
        this.audioPlayer.stop(this.src);
    }

    setPlaybackRate(rate) {
        this.audioPlayer.setPlaybackRate(this.src, rate);
    }
}