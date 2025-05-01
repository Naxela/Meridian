// assetManager.js - Asset loading system for SimpleBEX
import { log } from './utility.js';

export class AssetManager {
    /**
     * Create a new asset manager
     * @param {HTMLCanvasElement} canvas - The canvas element
     * @param {BABYLON.Engine} engine - The BabylonJS engine
     * @param {BABYLON.Scene} scene - The BabylonJS scene
     */
    constructor(canvas, engine, scene) {
        this.canvas = canvas;
        this.engine = engine;
        this.scene = scene;
        this.assetsManager = new BABYLON.AssetsManager(scene);
        
        // Configure default behavior
        this.assetsManager.useDefaultLoadingScreen = false;
        this.assetsManager.onProgress = this.onProgress.bind(this);
        this.assetsManager.onFinish = this.onFinish.bind(this);
        this.assetsManager.onTaskError = this.onTaskError.bind(this);
        
        // Store callback functions
        this.onLoadedCallback = null;
        this.onProgressCallback = null;
        this.onErrorCallback = null;
    }
    
    /**
     * Load a list of assets
     * @param {Array} assetList - List of assets to load
     * @param {Function} onLoaded - Callback function when all assets are loaded
     * @param {Function} onProgress - Callback function for loading progress
     * @param {Function} onError - Callback function for loading errors
     */
    loadAssets(assetList, onLoaded, onProgress, onError) {
        // Store callback functions
        this.onLoadedCallback = onLoaded;
        this.onProgressCallback = onProgress;
        this.onErrorCallback = onError;
        
        // Clear any previous tasks
        this.assetsManager.reset();
        
        // Process each asset in the list
        assetList.forEach(asset => {
            this.addAssetTask(asset);
        });
        
        // Start loading
        this.assetsManager.load();
    }
    
    /**
     * Add an asset task to the assets manager
     * @param {Object} asset - Asset configuration
     */
    addAssetTask(asset) {
        switch (asset.type) {
            case 'model':
                this.addModelTask(asset);
                break;
                
            case 'texture':
                this.addTextureTask(asset);
                break;
                
            case 'audio':
                this.addAudioTask(asset);
                break;
                
            case 'hdr':
                this.addHDRTask(asset);
                break;
                
            default:
                log(`Unsupported asset type: ${asset.type}`, true);
                break;
        }
    }
    
    /**
     * Add a model task to the assets manager
     * @param {Object} asset - Asset configuration
     */
    addModelTask(asset) {
        log(`Loading model: ${asset.url}`);
        
        const meshTask = this.assetsManager.addMeshTask(
            asset.name,
            "",
            asset.url.substring(0, asset.url.lastIndexOf('/') + 1),
            asset.url.substring(asset.url.lastIndexOf('/') + 1)
        );
        
        meshTask.onSuccess = task => {
            log(`Model loaded: ${task.name}`);
            
            // Process loaded meshes
            task.loadedMeshes.forEach(mesh => {
                // Add mesh to scene
                this.scene.addMesh(mesh);
                
                // Enable shadows
                mesh.receiveShadows = true;
                
                // Check for animations
                if (task.loadedAnimationGroups && task.loadedAnimationGroups.length > 0) {
                    task.loadedAnimationGroups.forEach(animGroup => {
                        log(`Animation group loaded: ${animGroup.name}`);
                    });
                }
            });
        };
        
        meshTask.onError = (task, message, exception) => {
            log(`Failed to load model: ${task.name} - ${message}`, true);
            
            if (this.onErrorCallback) {
                this.onErrorCallback(task, message, exception);
            }
        };
    }
    
    /**
     * Add a texture task to the assets manager
     * @param {Object} asset - Asset configuration
     */
    addTextureTask(asset) {
        log(`Loading texture: ${asset.url}`);
        
        const textureTask = this.assetsManager.addTextureTask(asset.name, asset.url);
        
        textureTask.onSuccess = task => {
            log(`Texture loaded: ${task.name}`);
            
            // Store loaded texture in scene
            this.scene[asset.name] = task.texture;
        };
    }
    
    /**
     * Add an audio task to the assets manager
     * @param {Object} asset - Asset configuration
     */
    addAudioTask(asset) {
        log(`Loading audio: ${asset.url}`);
        
        const audioTask = this.assetsManager.addBinaryFileTask(asset.name, asset.url);
        
        audioTask.onSuccess = task => {
            log(`Audio loaded: ${task.name}`);
            
            // Create audio
            const audioBuffer = task.data;
            
            // Store loaded audio buffer in scene
            this.scene[asset.name] = audioBuffer;
        };
    }
    
    /**
     * Add an HDR task to the assets manager
     * @param {Object} asset - Asset configuration
     */
    addHDRTask(asset) {
        log(`Loading HDR: ${asset.url}`);
        
        const hdrTask = this.assetsManager.addCubeTextureTask(asset.name, asset.url);
        
        hdrTask.onSuccess = task => {
            log(`HDR loaded: ${task.name}`);
            
            // Create environment from HDR
            const hdrTexture = task.texture;
            this.scene.environmentTexture = hdrTexture;
        };
    }
    
    /**
     * Handle asset loading progress
     * @param {number} remainingCount - Number of remaining tasks
     * @param {number} totalCount - Total number of tasks
     * @param {BABYLON.AbstractAssetTask} lastFinishedTask - Last finished task
     */
    onProgress(remainingCount, totalCount, lastFinishedTask) {
        const progress = (totalCount - remainingCount) / totalCount;
        
        // Call progress callback if defined
        if (this.onProgressCallback) {
            this.onProgressCallback(progress);
        }
    }
    
    /**
     * Handle asset loading finished
     * @param {Array} tasks - List of completed tasks
     */
    onFinish(tasks) {
        log('All assets loaded');
        
        // Call loaded callback if defined
        if (this.onLoadedCallback) {
            this.onLoadedCallback(tasks);
        }
    }
    
    /**
     * Handle asset loading error
     * @param {BABYLON.AbstractAssetTask} task - Failed task
     * @param {string} message - Error message
     * @param {Error} exception - Error exception
     */
    onTaskError(task, message, exception) {
        log(`Error loading asset: ${message}`, true);
        
        // Call error callback if defined
        if (this.onErrorCallback) {
            this.onErrorCallback(task, message, exception);
        }
    }
}