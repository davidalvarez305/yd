import { AudioHandler } from "./AudioHandler";
import AudioMessage from "./AudioMessage";

document.addEventListener("DOMContentLoaded", function() {
    const audioHandler = new AudioHandler();
    const audioMessages = document.querySelectorAll('.audioMessage');

    audioMessages.forEach(function (message) {
        const { audio, messageId } = message.dataset;

        if (!audio || !messageId) {
            console.error('Missing audio src or messageId for audio message');
            return;
        }

        audioHandler.addAudioMessage(new AudioMessage(audio, messageId));
    });
});