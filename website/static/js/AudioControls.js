import { AudioHandler } from "./AudioHandler.js";

/**
 * @param {AudioHandler} audioHandler
*/
export class AudioControls {
    constructor(audioHandler) {
        this.audioHandler = audioHandler
    }

    handleClickPlayButton() {
        this.audioHandler.handleBeginPlayback();
    }

    handleClickPauseButton() {
        this.audioHandler.handlePausePlayback();
    }

    handleClickStopButton() {
        this.audioHandler.handleStopPlayback();
    }

    handleClickAdjustPlaybackRateButton() {
        this.audioHandler.handleAdjustPlaybackRate();
    }

    _scanAudioControlButtons() {
        const beginPlaybackButtons = document.querySelectorAll('.beginPlayback');
        const stopPlaybackButtons = document.querySelectorAll('.stopPlayback');
        const pausePlaybackButtons = document.querySelectorAll('.pausePlayback');
        const adjustPlaybackRateButtons = document.querySelectorAll('.adjustPlaybackRate');
    
        if (beginPlaybackButtons.length === 0) {
            throw new Error('Cannot find begin playback buttons.');
        }
    
        if (stopPlaybackButtons.length === 0) {
            throw new Error('Cannot find stop playback buttons.');
        }
    
        if (pausePlaybackButtons.length === 0) {
            throw new Error('Cannot find pause playback buttons.');
        }
    
        if (adjustPlaybackRateButtons.length === 0) {
            throw new Error('Cannot find adjust playback rate buttons.');
        }
    
        beginPlaybackButtons.forEach((button) => {
            button.addEventListener("click", () => this.handleClickPlayButton());
        });
    
        stopPlaybackButtons.forEach((button) => {
            button.addEventListener("click", () => this.handleClickStopButton());
        });
    
        pausePlaybackButtons.forEach((button) => {
            button.addEventListener("click", () => this.handleClickPauseButton());
        });
    
        adjustPlaybackRateButtons.forEach((button) => {
            button.addEventListener("click", () => this.handleClickAdjustPlaybackRateButton());
        });
    }
}