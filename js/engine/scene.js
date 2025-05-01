// scene.js - Scene management for SimpleBEX
import { setupCamera } from './camera.js';
import { setupLights } from './light.js';
import { AssetManager } from './assetManager.js';
import { log } from './utility.js';

export class Scene {
    /**
     * Create a new scene
     * @param {BABYLON.Engine} engine - The BabylonJS engine
     * @param {SimpleBEXApp} app - The main application
     */
    constructor(engine, app) {
        this.engine = engine;
        this.app = app;
        this.babylonScene = new BABYLON.Scene(engine);
        this.activeCamera = null;
        this.assetManager = null;
    }

    /**
     * Initialize the scene
     */
    async initialize() {
        log('Creating scene');
        
        // Setup environment
        this.createEnvironment();
        
        // Setup asset manager
        this.assetManager = new AssetManager(this.app.canvas, this.engine, this.babylonScene);
        
        // Setup camera
        this.app.updateLoadingProgress(40, 'Setting up camera...');
        this.setupCamera();
        
        // Load assets
        this.app.updateLoadingProgress(50, 'Loading assets...');
        await this.loadAssets();
        
        // Setup lights
        this.app.updateLoadingProgress(70, 'Setting up lights...');
        this.setupLights();
        
        // Setup action manager for interactivity
        this.app.updateLoadingProgress(80, 'Setting up interactions...');
        this.setupActionManager();
        
        return this;
    }

    /**
     * Create the environment
     */
    createEnvironment() {
        const sceneData = this.app.projectData.manifest.scenes[0];
        const envData = sceneData.environment || {};
        
        if (envData.backgroundType === "color") {
            const color = envData.backgroundColor || [0.1, 0.1, 0.1];
            this.babylonScene.clearColor = new BABYLON.Color4(color[0], color[1], color[2], 1.0);
            this.babylonScene.ambientColor = new BABYLON.Color3(color[0], color[1], color[2]);
        } else if (envData.backgroundType === "texture" || envData.backgroundType === "sky") {
            this.babylonScene.clearColor = new BABYLON.Color4(0.1, 0.1, 0.1, 1.0);
            this.babylonScene.ambientColor = new BABYLON.Color3(0.3, 0.3, 0.3);
            
            // Create skybox if data is available
            if (envData.skyboxTexture) {
                const skybox = BABYLON.MeshBuilder.CreateBox("skyBox", { size: 1000.0 }, this.babylonScene);
                const skyboxMaterial = new BABYLON.StandardMaterial("skyBoxMaterial", this.babylonScene);
                skyboxMaterial.backFaceCulling = false;
                skyboxMaterial.reflectionTexture = new BABYLON.CubeTexture(envData.skyboxTexture, this.babylonScene);
                skyboxMaterial.reflectionTexture.coordinatesMode = BABYLON.Texture.SKYBOX_MODE;
                skyboxMaterial.diffuseColor = new BABYLON.Color3(0, 0, 0);
                skyboxMaterial.specularColor = new BABYLON.Color3(0, 0, 0);
                skybox.material = skyboxMaterial;
            }
        } else {
            // Default fallback
            this.babylonScene.clearColor = new BABYLON.Color4(0.1, 0.1, 0.1, 1.0);
            this.babylonScene.ambientColor = new BABYLON.Color3(0.3, 0.3, 0.3);
        }
    }

    /**
     * Setup camera
     */
    setupCamera() {
        const cameraData = this.app.projectData.manifest.scenes[0].scene_cameras?.[0];
        
        if (cameraData) {
            // Use camera data from project file
            this.activeCamera = setupCamera(this.babylonScene, this.app.canvas, cameraData);
        } else {
            // Create default camera
            this.activeCamera = new BABYLON.ArcRotateCamera(
                "defaultCamera",
                Math.PI / 3,
                Math.PI / 3,
                10,
                BABYLON.Vector3.Zero(),
                this.babylonScene
            );
            
            this.activeCamera.setTarget(BABYLON.Vector3.Zero());
            this.activeCamera.attachControl(this.app.canvas, true);
            this.activeCamera.wheelPrecision = 50.0;
        }
        
        this.babylonScene.activeCamera = this.activeCamera;
    }

    /**
     * Load assets
     */
    async loadAssets() {
        const sceneData = this.app.projectData.manifest.scenes[0];
        const assetsList = [];
        
        // Add models from glb_groups
        if (sceneData.glb_groups && sceneData.glb_groups.length) {
            sceneData.glb_groups.forEach(glbFile => {
                assetsList.push({
                    type: "model",
                    name: `model_${assetsList.length}`,
                    url: `assets/${glbFile}`
                });
            });
        }
        
        // Load other assets if defined
        // Could include textures, audio, etc.
        
        // Return a promise that resolves when all assets are loaded
        return new Promise((resolve, reject) => {
            this.assetManager.loadAssets(assetsList, resolve, (progress) => {
                // Update loading progress based on asset loading progress
                const loadingPercent = 50 + Math.floor(progress * 20);
                this.app.updateLoadingProgress(loadingPercent, 'Loading assets...');
            }, reject);
        });
    }

    /**
     * Setup lights
     */
    setupLights() {
        const sceneData = this.app.projectData.manifest.scenes[0];
        
        if (sceneData.scene_lights && sceneData.scene_lights.length) {
            // Create lights from project data
            sceneData.scene_lights.forEach(lightData => {
                setupLights(this.babylonScene, this.app.canvas, lightData);
            });
        } else {
            // Create default lights
            const hemisphericLight = new BABYLON.HemisphericLight(
                "defaultLight",
                new BABYLON.Vector3(0, 1, 0),
                this.babylonScene
            );
            hemisphericLight.intensity = 0.7;
            
            const directionalLight = new BABYLON.DirectionalLight(
                "directionalLight",
                new BABYLON.Vector3(-1, -2, -1),
                this.babylonScene
            );
            directionalLight.intensity = 0.5;
            
            // Setup shadows for directional light
            const shadowGenerator = new BABYLON.ShadowGenerator(1024, directionalLight);
            shadowGenerator.useBlurExponentialShadowMap = true;
            shadowGenerator.blurScale = 2;
            
            // Add meshes to shadow generator
            this.babylonScene.meshes.forEach(mesh => {
                if (!mesh.name.includes("skyBox")) {
                    shadowGenerator.addShadowCaster(mesh);
                    mesh.receiveShadows = true;
                }
            });
        }
    }

    /**
     * Setup action manager for interactivity
     */
    setupActionManager() {
        const actionManager = new BABYLON.ActionManager(this.babylonScene);
        
        // Apply action manager to all meshes
        this.babylonScene.meshes.forEach(mesh => {
            // Exclude skybox and other utility meshes
            if (!mesh.name.includes("skyBox")) {
                mesh.actionManager = actionManager;
            }
        });
        
        // Register hover action
/*         actionManager.registerAction(
            new BABYLON.ExecuteCodeAction(
                BABYLON.ActionManager.OnPointerOverTrigger,
                (evt) => {
                    const mesh = evt.source;
                    log(`Hover: ${mesh.name}`);
                    
                    // Optional: Visual feedback on hover
                    if (mesh.material) {
                        mesh._originalEmissive = mesh.material.emissiveColor?.clone();
                        mesh.material.emissiveColor = new BABYLON.Color3(0.2, 0.2, 0.2);
                    }
                }
            )
        ); */
        
        // Register hover out action
/*         actionManager.registerAction(
            new BABYLON.ExecuteCodeAction(
                BABYLON.ActionManager.OnPointerOutTrigger,
                (evt) => {
                    const mesh = evt.source;
                    
                    // Restore original emissive color
                    if (mesh.material && mesh._originalEmissive) {
                        mesh.material.emissiveColor = mesh._originalEmissive;
                    }
                }
            )
        ); */
        
        // Register click action
/*         actionManager.registerAction(
            new BABYLON.ExecuteCodeAction(
                BABYLON.ActionManager.OnPickTrigger,
                (evt) => {
                    const mesh = evt.source;
                    log(`Clicked: ${mesh.name}`);
                    
                    // Trigger custom event that can be listened to elsewhere
                    const event = new CustomEvent('meshClicked', { detail: { mesh } });
                    window.dispatchEvent(event);
                }
            )
        ); */
    }
}