import { AudioHandler } from "./AudioHandler.js";
import { AudioMessage } from "./AudioMessage.js";
import { createAudioPlayerFactory } from "./audioPlayerFactory.js";

document.addEventListener("DOMContentLoaded", async function () {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        const mediaRecorder = new MediaRecorder(stream);

        const audioPlayer = createAudioPlayerFactory();

        const audioHandler = new AudioHandler(mediaRecorder);

        const audioMessages = document.querySelectorAll('.audioMessage');
        audioMessages.forEach(function (message) {
            if (!message.dataset.src) {
                console.error('Missing audio src for audio message');
                return;
            }

            const audio = new AudioMessage(message.dataset.src, audioPlayer);
            audioHandler.registerAudioMessage(audio);
        });

    } catch (error) {
        console.error("Could not initialize audio recording:", error);
        throw new Error("Microphone access denied or unavailable.");
    }
});