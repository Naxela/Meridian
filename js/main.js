// main.js - Entry point for SimpleBEX application
import { SimpleBEXApp } from './app.js';

// Wait for DOM to be fully loaded
window.addEventListener('DOMContentLoaded', () => {
    // Get the canvas element
    const canvas = document.getElementById('renderCanvas');
    
    // Create the app with project file path
    // The project file contains scene configuration
    const app = new SimpleBEXApp(canvas, 'assets/project.json');
    
    // Handle window resize
    window.addEventListener('resize', () => app.resize());
    
    // Optional: Handle fullscreen toggle
    document.addEventListener('keydown', (event) => {
        if (event.key === 'f') {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                canvas.requestFullscreen().catch(err => {
                    console.error(`Error attempting to enable fullscreen: ${err.message}`);
                });
            }
        }
    });
});