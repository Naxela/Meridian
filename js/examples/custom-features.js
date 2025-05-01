// custom-features.js - Examples of extending SimpleBEX with custom features

/**
 * This file demonstrates how to extend SimpleBEX with custom functionality.
 * Import these functions into your main.js or create your own extensions.
 */

import { log } from '../engine/utility.js';

/**
 * Add object picking with highlightinq and information display
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 */
export function addObjectPicking(scene) {
    // Create a simple UI overlay for object information
    const infoPanel = document.createElement('div');
    infoPanel.style.position = 'absolute';
    infoPanel.style.bottom = '10px';
    infoPanel.style.left = '10px';
    infoPanel.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    infoPanel.style.color = 'white';
    infoPanel.style.padding = '10px';
    infoPanel.style.borderRadius = '5px';
    infoPanel.style.fontFamily = 'Arial, sans-serif';
    infoPanel.style.fontSize = '14px';
    infoPanel.style.display = 'none';
    document.body.appendChild(infoPanel);

    // Store original materials for highlighted objects
    const originalMaterials = new Map();
    let highlightedMesh = null;

    // Create a highlight material
    const highlightMaterial = new BABYLON.StandardMaterial('highlightMaterial', scene);
    highlightMaterial.diffuseColor = new BABYLON.Color3(1, 0.8, 0.3);
    highlightMaterial.specularColor = new BABYLON.Color3(1, 1, 1);
    highlightMaterial.emissiveColor = new BABYLON.Color3(0.3, 0.3, 0);
    highlightMaterial.alpha = 0.8;

    // Handle pointer move for object highlighting
    scene.onPointerMove = (evt, pickResult) => {
        if (pickResult.hit && pickResult.pickedMesh) {
            const mesh = pickResult.pickedMesh;
            
            // Skip if it's the current highlighted mesh or a non-pickable mesh
            if (mesh === highlightedMesh || mesh.name.includes('skyBox')) {
                return;
            }
            
            // Reset previous highlighted mesh
            if (highlightedMesh && originalMaterials.has(highlightedMesh)) {
                highlightedMesh.material = originalMaterials.get(highlightedMesh);
                originalMaterials.delete(highlightedMesh);
                highlightedMesh = null;
                infoPanel.style.display = 'none';
            }
            
            // Highlight new mesh
            if (mesh.material) {
                originalMaterials.set(mesh, mesh.material);
                mesh.material = highlightMaterial;
                highlightedMesh = mesh;
                
                // Show info panel with mesh details
                infoPanel.innerHTML = `
                    <strong>${mesh.name}</strong><br>
                    Vertices: ${mesh.getTotalVertices()}<br>
                    Triangles: ${mesh.getTotalIndices() / 3}
                `;
                infoPanel.style.display = 'block';
            }
        } else if (highlightedMesh) {
            // Reset highlighted mesh when not hovering over any mesh
            highlightedMesh.material = originalMaterials.get(highlightedMesh);
            originalMaterials.delete(highlightedMesh);
            highlightedMesh = null;
            infoPanel.style.display = 'none';
        }
    };

    // Handle pointer up for object selection
    scene.onPointerUp = (evt, pickResult) => {
        if (pickResult.hit && pickResult.pickedMesh) {
            const mesh = pickResult.pickedMesh;
            
            if (!mesh.name.includes('skyBox')) {
                log(`Selected object: ${mesh.name}`);
                
                // Trigger a custom event for object selection
                const event = new CustomEvent('objectSelected', {
                    detail: { mesh }
                });
                window.dispatchEvent(event);
            }
        }
    };
}

/**
 * Add first-person controller with physics
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 * @param {BABYLON.Camera} camera - The camera to control
 */
export function addFirstPersonController(scene, camera) {
    // Ensure the camera is a universal or free camera
    if (!(camera instanceof BABYLON.UniversalCamera || camera instanceof BABYLON.FreeCamera)) {
        log('First person controller requires a Universal or Free camera', true);
        return;
    }
    
    // Enable camera collision
    camera.checkCollisions = true;
    camera.applyGravity = true;
    camera.ellipsoid = new BABYLON.Vector3(1, 0.9, 1);
    camera.ellipsoidOffset = new BABYLON.Vector3(0, 0.9, 0);
    
    // Set scene gravity (only affects objects with applyGravity enabled)
    scene.gravity = new BABYLON.Vector3(0, -9.81, 0);
    
    // Set camera initial position and rotation
    camera.position = new BABYLON.Vector3(0, 2, 0);
    camera.rotation = new BABYLON.Vector3(0, 0, 0);
    
    // Lock target for consistent orientation
    camera.lockedTarget = null;
    
    // Set camera control properties
    camera.speed = 0.5;
    camera.inertia = 0.3;
    camera.angularSensibility = 1000;
    
    // Set camera inputs for WASD and arrow key controls
    camera.keysUp = [87, 38]; // W, Up arrow
    camera.keysDown = [83, 40]; // S, Down arrow
    camera.keysLeft = [65, 37]; // A, Left arrow
    camera.keysRight = [68, 39]; // D, Right arrow
    
    // Add jump functionality
    let isJumping = false;
    let jumpForce = 0.1;
    
    scene.onKeyboardObservable.add((kbInfo) => {
        if (kbInfo.type === BABYLON.KeyboardEventTypes.KEYDOWN) {
            // Jump with Space key
            if (kbInfo.event.keyCode === 32 && !isJumping) {
                isJumping = true;
                
                // Apply upward velocity
                camera.cameraDirection.y += jumpForce;
                
                // Reset jump after a short delay
                setTimeout(() => {
                    isJumping = false;
                }, 1000);
            }
        }
    });
    
    // Setup pointer lock for immersive control
    scene.onPointerDown = (evt) => {
        if (!document.pointerLockElement) {
            scene.getEngine().getRenderingCanvas().requestPointerLock = 
                scene.getEngine().getRenderingCanvas().requestPointerLock || 
                scene.getEngine().getRenderingCanvas().mozRequestPointerLock;
            scene.getEngine().getRenderingCanvas().requestPointerLock();
        }
    };
}

/**
 * Add a simple particle system
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 * @param {BABYLON.Vector3} position - Position to emit particles
 * @param {BABYLON.Color4} color - Particle color
 */
export function addParticleSystem(scene, position, color = new BABYLON.Color4(1, 0.5, 0, 1)) {
    // Create a particle system
    const particleSystem = new BABYLON.ParticleSystem('particles', 2000, scene);
    
    // Set particle texture
    particleSystem.particleTexture = new BABYLON.Texture('assets/textures/particle.png', scene);
    
    // Set emitter position
    particleSystem.emitter = position;
    particleSystem.minEmitBox = new BABYLON.Vector3(-0.5, 0, -0.5);
    particleSystem.maxEmitBox = new BABYLON.Vector3(0.5, 0, 0.5);
    
    // Set particle colors
    particleSystem.color1 = color;
    particleSystem.color2 = new BABYLON.Color4(color.r * 0.8, color.g * 0.8, color.b * 0.8, color.a);
    particleSystem.colorDead = new BABYLON.Color4(0, 0, 0, 0);
    
    // Set particle sizes and lifetime
    particleSystem.minSize = 0.1;
    particleSystem.maxSize = 0.5;
    particleSystem.minLifeTime = 0.3;
    particleSystem.maxLifeTime = 1.5;
    
    // Set emission rate and power
    particleSystem.emitRate = 500;
    particleSystem.minEmitPower = 1;
    particleSystem.maxEmitPower = 3;
    particleSystem.updateSpeed = 0.005;
    
    // Set particle direction and gravity
    particleSystem.direction1 = new BABYLON.Vector3(-1, 4, 1);
    particleSystem.direction2 = new BABYLON.Vector3(1, 4, -1);
    particleSystem.gravity = new BABYLON.Vector3(0, -9.81, 0);
    
    // Start the particle system
    particleSystem.start();
    
    return particleSystem;
}

/**
 * Add post-processing effects
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 * @param {BABYLON.Camera} camera - The camera to apply effects to
 */
export function addPostProcessing(scene, camera) {
    // Create default rendering pipeline
    const pipeline = new BABYLON.DefaultRenderingPipeline('pipeline', true, scene, [camera]);
    
    // Enable image processing
    pipeline.imageProcessingEnabled = true;
    pipeline.imageProcessing.exposure = 1.2;
    pipeline.imageProcessing.contrast = 1.1;
    
    // Enable tone mapping for better lighting
    pipeline.imageProcessing.toneMappingEnabled = true;
    pipeline.imageProcessing.toneMappingType = BABYLON.ImageProcessingPostProcess.TONEMAPPING_ACES;
    
    // Enable anti-aliasing
    pipeline.samples = 4;
    pipeline.fxaaEnabled = true;
    
    // Enable bloom
    pipeline.bloomEnabled = true;
    pipeline.bloomThreshold = 0.8;
    pipeline.bloomWeight = 0.3;
    pipeline.bloomKernel = 64;
    pipeline.bloomScale = 0.5;
    
    // Enable depth of field
    pipeline.depthOfFieldEnabled = true;
    pipeline.depthOfFieldBlurLevel = BABYLON.DepthOfFieldEffectBlurLevel.Low;
    pipeline.depthOfField.focalLength = 150;
    pipeline.depthOfField.fStop = 1.4;
    pipeline.depthOfField.focusDistance = 2000;
    
    // Add chromatic aberration
    pipeline.chromaticAberrationEnabled = true;
    pipeline.chromaticAberration.aberrationAmount = 1;
    pipeline.chromaticAberration.radialIntensity = 0.5;
    
    // Add vignette effect
    pipeline.vignetteEnabled = true;
    pipeline.vignette.color = new BABYLON.Color4(0, 0, 0, 0);
    pipeline.vignette.intensity = 0.25;
    
    return pipeline;
}