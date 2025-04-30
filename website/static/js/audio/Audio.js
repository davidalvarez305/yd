import { AudioHandler } from "./AudioHandler.js";
import { AudioControlPanel } from "./AudioControlPanel.js";

document.addEventListener("DOMContentLoaded", async () => {
    try {
        const audioHandler = new AudioHandler();
        await audioHandler.init();

        const audioControlPanel = new AudioControlPanel(audioHandler);

        audioControlPanel.scanAudioElements();
    }
    catch (error) {
        throw new Error('Failed to initialize audio handler: ', error);
    }
});
