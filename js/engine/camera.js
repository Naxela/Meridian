// camera.js - Camera management for SimpleBEX
import { log } from './utility.js';

/**
 * Create and setup a camera based on configuration data
 * @param {BABYLON.Scene} scene - The BabylonJS scene
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @param {Object} cameraData - Camera configuration data
 * @returns {BABYLON.Camera} - The created camera
 */
export function setupCamera(scene, canvas, cameraData) {
    log(`Creating camera: ${cameraData.name || 'Universal Camera'}`);
    
    // Create a universal camera
    const camera = new BABYLON.UniversalCamera(
        cameraData.name || "MainCamera",
        new BABYLON.Vector3(0, 0, 0),
        scene
    );
    
    // Apply camera transformation from the configuration
    if (cameraData.matrix) {
        applyTransformation(camera, cameraData.matrix);
    } else {
        // Default position if no matrix provided
        camera.position = new BABYLON.Vector3(0, 2, -10);
        camera.rotation = new BABYLON.Vector3(0, 0, 0);
    }
    
    // Attach control to canvas
    camera.attachControl(canvas, true);
    
    // Set camera properties for walking and flying
    camera.speed = 2; // Base movement speed
    camera.inertia = 0.7; // Movement inertia
    camera.angularSensibility = 2000; // Mouse sensitivity
    
    // WASD controls
    camera.keysUp.push(87);    // W
    camera.keysDown.push(83);  // S
    camera.keysLeft.push(65);  // A
    camera.keysRight.push(68); // D
    camera.keysUpward = [69];  // E - Move up
    camera.keysDownward = [81]; // Q - Move down
    
    // Enable collision detection if specified in camera data
    camera.checkCollisions = cameraData.checkCollisions || false;
    camera.applyGravity = cameraData.applyGravity || false;
    camera.ellipsoid = new BABYLON.Vector3(1, 1, 1); // Collision ellipsoid
    
    // Setup camera behavior enhancements
    setupCameraEnhancements(camera, canvas);
    
    return camera;
}

/**
 * Apply transformation matrix to a camera
 * @param {BABYLON.Camera} camera - The camera to transform
 * @param {Array} matrix - 4x4 transformation matrix in column-major order
 */
function applyTransformation(camera, matrix) {
    // Convert to Babylon matrix and transpose (Babylon uses row-major matrices)
    const babylonMatrix = BABYLON.Matrix.FromArray(matrix).transpose();
    
    // Decompose into position, rotation, and scale
    const position = new BABYLON.Vector3();
    const rotationQuat = new BABYLON.Quaternion();
    const scale = new BABYLON.Vector3();
    
    babylonMatrix.decompose(scale, rotationQuat, position);
    
    // Apply position (invert X for right-to-left-handed conversion)
    camera.position = new BABYLON.Vector3(-position.x, position.y, position.z);
    
    // Convert quaternion to Euler angles
    const rotationMatrix = BABYLON.Matrix.Identity();
    rotationQuat.toRotationMatrix(rotationMatrix);
    
    // Create a rotation matrix for 180-degree Y-axis rotation (for right-to-left-handed conversion)
    const convertMatrix = BABYLON.Matrix.RotationY(Math.PI);
    
    // Combine the matrices
    const finalRotMatrix = BABYLON.Matrix.Identity();
    convertMatrix.multiplyToRef(rotationMatrix, finalRotMatrix);
    
    // Extract the final quaternion and convert to Euler angles
    const finalQuat = new BABYLON.Quaternion();
    BABYLON.Quaternion.FromRotationMatrixToRef(finalRotMatrix, finalQuat);
    const euler = finalQuat.toEulerAngles();
    
    // Apply rotation
    camera.rotation = new BABYLON.Vector3(euler.x, -euler.y, euler.z);
}

/**
 * Setup additional camera behavior enhancements
 * @param {BABYLON.Camera} camera - The camera to enhance
 * @param {HTMLCanvasElement} canvas - The canvas element
 */
function setupCameraEnhancements(camera, canvas) {
    // Track shift key state for speed boost
    let isShiftPressed = false;
    const defaultSpeed = 2;
    const fastSpeed = 20;
    
    window.addEventListener("keydown", (event) => {
        if (event.key === "Shift") {
            isShiftPressed = true;
            camera.speed = fastSpeed;
        }
    });
    
    window.addEventListener("keyup", (event) => {
        if (event.key === "Shift") {
            isShiftPressed = false;
            camera.speed = defaultSpeed;
        }
    });
    
    // Toggle gravity with space key
    window.addEventListener("keydown", (event) => {
        if (event.key === " ") {
            camera.applyGravity = !camera.applyGravity;
            log(`Gravity ${camera.applyGravity ? 'enabled' : 'disabled'}`);
        }
    });
    
    // Optional: Pointer Lock for FPS-style camera
    canvas.addEventListener("click", () => {
        if (canvas.requestPointerLock) {
            canvas.requestPointerLock();
        } else if (canvas.mozRequestPointerLock) {
            canvas.mozRequestPointerLock();
        } else if (canvas.webkitRequestPointerLock) {
            canvas.webkitRequestPointerLock();
        }
    });
    
    // Handle pointer lock changes
    const lockChangeHandler = () => {
        if (document.pointerLockElement === canvas ||
            document.mozPointerLockElement === canvas ||
            document.webkitPointerLockElement === canvas) {
            // Pointer is locked, add mousemove listener
            document.addEventListener("mousemove", updateCameraRotation, false);
        } else {
            // Pointer is unlocked, remove mousemove listener
            document.removeEventListener("mousemove", updateCameraRotation, false);
        }
    };
    
    // Update camera rotation based on mouse movement (in pointer lock mode)
    function updateCameraRotation(event) {
        if (camera.rotation) {
            camera.rotation.y += event.movementX * 0.002;
            camera.rotation.x += event.movementY * 0.002;
        }
    }
    
    // Add pointer lock change event listeners
    document.addEventListener("pointerlockchange", lockChangeHandler, false);
    document.addEventListener("mozpointerlockchange", lockChangeHandler, false);
    document.addEventListener("webkitpointerlockchange", lockChangeHandler, false);
}