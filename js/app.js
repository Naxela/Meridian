// app.js - Core application class for SimpleBEX
import { Scene } from './engine/scene.js';
import { loadJSON } from './engine/utility.js';

export class SimpleBEXApp {
    /**
     * Create a new SimpleBEX application
     * @param {HTMLCanvasElement} canvas - The canvas element for rendering
     * @param {string} projectFile - Path to the project configuration file
     */
    constructor(canvas, projectFile) {
        this.canvas = canvas;
        this.projectFile = projectFile;
        this.projectData = null;
        this.engine = null;
        this.scene = null;
        this.debugMode = false;
        
        // Start loading the project
        this.initialize();
    }

    /**
     * Initialize the application
     */
    async initialize() {
        try {
            // Show loading screen
            this.updateLoadingProgress(10, 'Loading project configuration...');
            
            // Load project configuration
            this.projectData = await loadJSON(this.projectFile);
            
            if (!this.projectData) {
                throw new Error('Failed to load project configuration');
            }
            
            this.updateLoadingProgress(20, 'Creating engine...');
            
            // Set debug mode
            this.debugMode = this.projectData.debug || false;
            
            // Set page title
            document.title = this.projectData.name || 'SimpleBEX Project';
            
            // Create the BabylonJS engine
            this.engine = new BABYLON.Engine(this.canvas, true);
            
            this.updateLoadingProgress(30, 'Creating scene...');
            
            // Create the scene
            this.scene = new Scene(this.engine, this);
            
            // Wait for scene to be fully loaded
            await this.scene.initialize();
            
            this.updateLoadingProgress(90, 'Starting render loop...');
            
            // Start the render loop
            this.run();
            
            this.updateLoadingProgress(100, 'Ready!');
            
            // Hide loading screen after a short delay
            setTimeout(() => {
                const loadingScreen = document.getElementById('loadingScreen');
                loadingScreen.style.opacity = '0';
                
                // Remove from DOM after fade out
                setTimeout(() => {
                    loadingScreen.style.display = 'none';
                }, 1000);
            }, 500);
            
        } catch (error) {
            console.error('Initialization error:', error);
            this.updateLoadingProgress(0, `Error: ${error.message}`);
        }
    }

    /**
     * Update the loading screen progress
     * @param {number} percent - Percentage complete (0-100)
     * @param {string} message - Status message to display
     */
    updateLoadingProgress(percent, message) {
        const progress = document.getElementById('loadingProgress');
        const loadingScreen = document.getElementById('loadingScreen');
        
        if (progress) {
            progress.style.width = `${percent}%`;
        }
        
        if (message && loadingScreen) {
            // Update the first div inside loadingScreen
            const messageElem = loadingScreen.querySelector('div');
            if (messageElem) {
                messageElem.textContent = message;
            }
        }
    }

    /**
     * Start the render loop
     */
    run() {
        // Enable debug layer if in debug mode
        if (this.debugMode && BABYLON.Inspector) {
            this.scene.babylonScene.debugLayer.show({
                embedMode: true,
                overlay: true
            });
        }

        // Run the render loop
        this.engine.runRenderLoop(() => {
            this.scene.babylonScene.render();
        });
    }

    /**
     * Handle window resize
     */
    resize() {
        if (this.engine) {
            this.engine.resize();
        }
    }
}