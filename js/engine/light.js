// light.js - Light setup for SimpleBEX
import { log } from './utility.js';

/**
 * Create and setup lights based on configuration data
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @param {Object} lightData - Light configuration data
 * @returns {BABYLON.Light} - The created light
 */
export function setupLights(scene, canvas, lightData) {
    log(`Creating light: ${lightData.name || 'unnamed'} (${lightData.type})`);
    
    let light;
    
    // Create light based on type
    switch (lightData.type) {
        case "POINT":
            light = createPointLight(scene, lightData);
            break;
        case "SPOT":
            light = createSpotLight(scene, lightData);
            break;
        case "SUN":
        case "DIRECTIONAL":
            light = createDirectionalLight(scene, lightData);
            break;
        default:
            // Create a default hemispheric light
            light = new BABYLON.HemisphericLight(
                lightData.name || "defaultLight",
                new BABYLON.Vector3(0, 1, 0),
                scene
            );
            break;
    }
    
    return light;
}

/**
 * Create a point light
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 * @param {Object} lightData - Light configuration data
 * @returns {BABYLON.PointLight} - The created point light
 */
function createPointLight(scene, lightData) {
    // Create a point light
    const light = new BABYLON.PointLight(
        lightData.name || "pointLight",
        new BABYLON.Vector3(0, 0, 0),
        scene
    );
    
    // Apply transformation from matrix
    if (lightData.matrix) {
        const position = getPositionFromMatrix(lightData.matrix);
        light.position = new BABYLON.Vector3(-position.x, position.y, position.z);
    }
    
    // Set light properties
    if (lightData.color) {
        light.diffuse = new BABYLON.Color3(lightData.color[0], lightData.color[1], lightData.color[2]);
        light.specular = new BABYLON.Color3(lightData.color[0], lightData.color[1], lightData.color[2]);
    }
    
    if (lightData.intensity !== undefined) {
        light.intensity = lightData.intensity;
    }
    
    // Set light range if specified
    if (lightData.range) {
        light.range = lightData.range;
    }
    
    return light;
}

/**
 * Create a spot light
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 * @param {Object} lightData - Light configuration data
 * @returns {BABYLON.SpotLight} - The created spot light
 */
function createSpotLight(scene, lightData) {
    // Create a spot light with initial position and direction
    const light = new BABYLON.SpotLight(
        lightData.name || "spotLight",
        new BABYLON.Vector3(0, 0, 0),
        new BABYLON.Vector3(0, 0, -1),
        lightData.angle || Math.PI / 4,
        lightData.exponent || 2,
        scene
    );
    
    // Apply transformation from matrix
    if (lightData.matrix) {
        const { position, direction } = getPositionAndDirectionFromMatrix(lightData.matrix);
        light.position = new BABYLON.Vector3(-position.x, position.y, position.z);
        light.direction = new BABYLON.Vector3(-direction.x, direction.y, direction.z);
    }
    
    // Set light properties
    if (lightData.color) {
        light.diffuse = new BABYLON.Color3(lightData.color[0], lightData.color[1], lightData.color[2]);
        light.specular = new BABYLON.Color3(lightData.color[0], lightData.color[1], lightData.color[2]);
    }
    
    if (lightData.intensity !== undefined) {
        light.intensity = lightData.intensity;
    }
    
    return light;
}

/**
 * Create a directional light
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 * @param {Object} lightData - Light configuration data
 * @returns {BABYLON.DirectionalLight} - The created directional light
 */
function createDirectionalLight(scene, lightData) {
    // Create a directional light
    const light = new BABYLON.DirectionalLight(
        lightData.name || "directionalLight",
        new BABYLON.Vector3(0, -1, 0),
        scene
    );
    
    // Apply transformation from matrix
    if (lightData.matrix) {
        const { position, direction } = getPositionAndDirectionFromMatrix(lightData.matrix);
        light.position = new BABYLON.Vector3(-position.x, position.y, position.z);
        light.direction = new BABYLON.Vector3(-direction.x, direction.y, direction.z);
    }
    
    // Set light properties
    if (lightData.color) {
        light.diffuse = new BABYLON.Color3(lightData.color[0], lightData.color[1], lightData.color[2]);
        light.specular = new BABYLON.Color3(lightData.color[0], lightData.color[1], lightData.color[2]);
    }
    
    if (lightData.intensity !== undefined) {
        light.intensity = lightData.intensity;
    }
    
    // Create shadow generator if specified
    if (lightData.castShadows) {
        const shadowGenerator = new BABYLON.ShadowGenerator(1024, light);
        
        // Add all meshes to shadow generator
        scene.meshes.forEach(mesh => {
            if (!mesh.name.includes("skyBox")) {
                shadowGenerator.getShadowMap().renderList.push(mesh);
                mesh.receiveShadows = true;
            }
        });
        
        // Configure shadow quality
        shadowGenerator.usePercentageCloserFiltering = true;
        shadowGenerator.bias = 0.00001;
    }
    
    return light;
}

/**
 * Extract position from a 4x4 transformation matrix
 * @param {Array} matrix - 4x4 transformation matrix in column-major order
 * @returns {BABYLON.Vector3} - The position vector
 */
function getPositionFromMatrix(matrix) {
    // Convert to Babylon matrix and transpose (Babylon uses row-major matrices)
    const babylonMatrix = BABYLON.Matrix.FromArray(matrix).transpose();
    
    // Decompose into position, rotation, and scale
    const position = new BABYLON.Vector3();
    const rotationQuat = new BABYLON.Quaternion();
    const scale = new BABYLON.Vector3();
    
    babylonMatrix.decompose(scale, rotationQuat, position);
    
    return position;
}

/**
 * Extract position and direction from a 4x4 transformation matrix
 * @param {Array} matrix - 4x4 transformation matrix in column-major order
 * @returns {Object} - Object containing position and direction vectors
 */
function getPositionAndDirectionFromMatrix(matrix) {
    // Convert to Babylon matrix and transpose (Babylon uses row-major matrices)
    const babylonMatrix = BABYLON.Matrix.FromArray(matrix).transpose();
    
    // Decompose into position, rotation, and scale
    const position = new BABYLON.Vector3();
    const rotationQuat = new BABYLON.Quaternion();
    const scale = new BABYLON.Vector3();
    
    babylonMatrix.decompose(scale, rotationQuat, position);
    
    // Create a rotation matrix from the quaternion
    const rotationMatrix = BABYLON.Matrix.Identity();
    rotationQuat.toRotationMatrix(rotationMatrix);
    
    // Transform the forward vector (0,0,-1) by the rotation matrix to get direction
    const forward = new BABYLON.Vector3(0, 0, -1);
    const direction = BABYLON.Vector3.TransformCoordinates(forward, rotationMatrix);
    
    return { position, direction };
}