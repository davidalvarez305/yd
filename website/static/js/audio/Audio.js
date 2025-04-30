import { AudioControlPanel } from "./AudioControlPanel.js";
import { AudioHandler } from "./AudioHandler.js";
import { AudioMessage } from "./AudioMessage.js";
import { createAudioPlayerFactory } from "./AudioPlayer.js";
import { Recording } from "./Recording.js";

document.addEventListener("DOMContentLoaded", async function () {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        const mediaRecorder = new MediaRecorder(stream);

        const audioPlayer = createAudioPlayerFactory();

        let recording = new Recording(audioPlayer);

        const audioHandler = new AudioHandler(mediaRecorder, recording);

        const audioControlPanel = new AudioControlPanel(audioHandler);

        audioControlPanel.scanAudioElements();

    } catch (error) {
        console.error("Could not initialize audio recording:", error);
        throw new Error("Microphone access denied or unavailable.");
    }
});