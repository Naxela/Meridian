// utility.js - Utility functions for SimpleBEX

/**
 * Log a message to the console
 * @param {string} message - Message to log
 * @param {boolean} isError - Whether this is an error message
 */
export function log(message, isError = false) {
    const timestamp = getTimestamp();
    
    if (isError) {
        console.error(`${timestamp} [ERROR] ${message}`);
    } else {
        console.log(`${timestamp} ${message}`);
    }
}

/**
 * Get the current timestamp
 * @returns {string} - Formatted timestamp
 */
export function getTimestamp() {
    const now = new Date();
    return `[${now.toISOString()}]`;
}

/**
 * Load a JSON file
 * @param {string} url - URL of the JSON file
 * @returns {Promise<Object>} - Promise that resolves with the parsed JSON
 */
export async function loadJSON(url) {
    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const text = await response.text();
        return JSON.parse(text);
    } catch (error) {
        log(`Failed to load JSON from ${url}: ${error.message}`, true);
        return null;
    }
}

/**
 * Load an arbitrary file as text
 * @param {string} url - URL of the file
 * @returns {Promise<string>} - Promise that resolves with the file contents
 */
export async function loadTextFile(url) {
    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        return await response.text();
    } catch (error) {
        log(`Failed to load text from ${url}: ${error.message}`, true);
        return null;
    }
}

/**
 * Generate a unique ID
 * @returns {string} - Unique ID
 */
export function generateUniqueId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Add an HDR loader to BabylonJS
 */
export function setupHDRLoader() {
    // This adds an HDR texture loader to BabylonJS
    // Note: Most current versions of BabylonJS already include HDR support,
    // but this is included for compatibility with older versions
    if (BABYLON.ThinEngine && BABYLON.ThinEngine._TextureLoaders) {
        BABYLON.ThinEngine._TextureLoaders.splice(0, 0, {
            supportCascades: false,
            
            canLoad: (extension) => {
                return extension.toLowerCase() === ".hdr";
            },
            
            loadData: (data, texture, callback) => {
                const bytes = new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
                
                const hdrInfo = BABYLON.HDRTools.RGBE_ReadHeader(bytes);
                const pixels = BABYLON.HDRTools.RGBE_ReadPixels(bytes, hdrInfo);
                
                texture.type = BABYLON.Constants.TEXTURETYPE_FLOAT;
                texture.format = BABYLON.Constants.TEXTUREFORMAT_RGB;
                
                // Mip maps can't be generated on FLOAT RGB textures
                texture.generateMipMaps = false;
                
                callback(hdrInfo.width, hdrInfo.height, texture.generateMipMaps, false, () => {
                    texture.getEngine()._uploadDataToTextureDirectly(texture, pixels, 0, 0, undefined, true);
                });
            }
        });
    }
}

/**
 * Deep clone an object
 * @param {Object} obj - Object to clone
 * @returns {Object} - Cloned object
 */
export function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

/**
 * Create a simple project configuration file
 * @param {string} name - Project name
 * @returns {Object} - Project configuration object
 */
export function createDefaultProject(name = "SimpleBEX Project") {
    return {
        name,
        version: "1.0.0",
        debug: false,
        manifest: {
            scenes: [
                {
                    name: "DefaultScene",
                    environment: {
                        backgroundType: "color",
                        backgroundColor: [0.1, 0.1, 0.1]
                    },
                    scene_cameras: [
                        {
                            name: "MainCamera",
                            type: "UNIVERSAL",
                            matrix: [
                                1, 0, 0, 0,
                                0, 1, 0, 0,
                                0, 0, 1, 0,
                                0, 2, -10, 1
                            ]
                        }
                    ],
                    scene_lights: [
                        {
                            name: "MainLight",
                            type: "SUN",
                            color: [1, 1, 1],
                            intensity: 1,
                            castShadows: true,
                            matrix: [
                                1, 0, 0, 0,
                                0, 1, 0, 0,
                                0, 0, 1, 0,
                                0, 10, 0, 1
                            ]
                        }
                    ],
                    glb_groups: []
                }
            ]
        }
    };
}