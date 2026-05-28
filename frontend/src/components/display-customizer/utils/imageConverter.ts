/**
 * Image Converter Utilities for ESP32 Display
 * Converts images to RGB565 and Monochrome formats
 */

/**
 * Convert an image file to RGB565 format for LCD displays
 * RGB565: 5 bits red, 6 bits green, 5 bits blue (16-bit per pixel)
 */
export async function convertImageToRGB565(
    imageSource: File | string,
    targetWidth: number,
    targetHeight: number
): Promise<Uint16Array> {
    return new Promise((resolve, reject) => {
        const img = new Image();
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        if (!ctx) {
            reject(new Error("Canvas 2D context not supported"));
            return;
        }

        img.onload = () => {
            // Set canvas to target dimensions
            canvas.width = targetWidth;
            canvas.height = targetHeight;

            // Draw image scaled to fit
            ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

            // Get pixel data
            const imageData = ctx.getImageData(0, 0, targetWidth, targetHeight);
            const pixels = imageData.data;

            // Convert to RGB565
            const rgb565 = new Uint16Array(targetWidth * targetHeight);

            for (let i = 0; i < pixels.length; i += 4) {
                const r = pixels[i];
                const g = pixels[i + 1];
                const b = pixels[i + 2];

                // RGB565: RRRRR GGGGGG BBBBB
                const r5 = (r >> 3) & 0x1f;
                const g6 = (g >> 2) & 0x3f;
                const b5 = (b >> 3) & 0x1f;

                rgb565[i / 4] = (r5 << 11) | (g6 << 5) | b5;
            }

            resolve(rgb565);
        };

        img.onerror = () => reject(new Error("Failed to load image"));

        // Handle both File and base64 string
        if (typeof imageSource === "string") {
            img.src = imageSource;
        } else {
            img.src = URL.createObjectURL(imageSource);
        }
    });
}

/**
 * Convert an image to monochrome (1-bit) for OLED displays
 * Each bit represents a pixel (1 = white, 0 = black)
 */
export async function convertImageToMono(
    imageSource: File | string,
    targetWidth: number,
    targetHeight: number,
    threshold: number = 128
): Promise<Uint8Array> {
    return new Promise((resolve, reject) => {
        const img = new Image();
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        if (!ctx) {
            reject(new Error("Canvas 2D context not supported"));
            return;
        }

        img.onload = () => {
            canvas.width = targetWidth;
            canvas.height = targetHeight;
            ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

            const imageData = ctx.getImageData(0, 0, targetWidth, targetHeight);
            const pixels = imageData.data;

            // 1 bit per pixel, packed into bytes (8 pixels per byte)
            const byteWidth = Math.ceil(targetWidth / 8);
            const mono = new Uint8Array(byteWidth * targetHeight);

            for (let y = 0; y < targetHeight; y++) {
                for (let x = 0; x < targetWidth; x++) {
                    const i = (y * targetWidth + x) * 4;
                    // Grayscale conversion: 0.299*R + 0.587*G + 0.114*B
                    const gray =
                        0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2];

                    if (gray >= threshold) {
                        const byteIndex = y * byteWidth + Math.floor(x / 8);
                        const bitIndex = 7 - (x % 8);
                        mono[byteIndex] |= 1 << bitIndex;
                    }
                }
            }

            resolve(mono);
        };

        img.onerror = () => reject(new Error("Failed to load image"));

        if (typeof imageSource === "string") {
            img.src = imageSource;
        } else {
            img.src = URL.createObjectURL(imageSource);
        }
    });
}

/**
 * Convert a hex color string to RGB565 value
 */
export function hexToRGB565(hex: string): number {
    // Remove # if present
    hex = hex.replace("#", "");

    // Parse RGB values
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);

    // Convert to RGB565
    const r5 = (r >> 3) & 0x1f;
    const g6 = (g >> 2) & 0x3f;
    const b5 = (b >> 3) & 0x1f;

    return (r5 << 11) | (g6 << 5) | b5;
}

/**
 * Resize an image maintaining aspect ratio
 * Returns base64 encoded result
 */
export async function resizeImage(
    imageSource: File | string,
    maxWidth: number,
    maxHeight: number,
    format: "jpeg" | "png" = "jpeg",
    quality: number = 0.85
): Promise<string> {
    return new Promise((resolve, reject) => {
        const img = new Image();
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        if (!ctx) {
            reject(new Error("Canvas 2D context not supported"));
            return;
        }

        img.onload = () => {
            // Calculate aspect ratio preserving dimensions
            let width = img.width;
            let height = img.height;

            if (width > maxWidth) {
                height = (height * maxWidth) / width;
                width = maxWidth;
            }

            if (height > maxHeight) {
                width = (width * maxHeight) / height;
                height = maxHeight;
            }

            canvas.width = width;
            canvas.height = height;

            // Enable image smoothing for better quality
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = "high";

            ctx.drawImage(img, 0, 0, width, height);

            const mimeType = format === "jpeg" ? "image/jpeg" : "image/png";
            resolve(canvas.toDataURL(mimeType, quality));
        };

        img.onerror = () => reject(new Error("Failed to load image"));

        if (typeof imageSource === "string") {
            img.src = imageSource;
        } else {
            img.src = URL.createObjectURL(imageSource);
        }
    });
}

/**
 * Convert File to base64 string
 */
export function fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

/**
 * Get image dimensions from a File or base64 string
 */
export function getImageDimensions(
    imageSource: File | string
): Promise<{ width: number; height: number }> {
    return new Promise((resolve, reject) => {
        const img = new Image();

        img.onload = () => {
            resolve({ width: img.width, height: img.height });
        };

        img.onerror = () => reject(new Error("Failed to load image"));

        if (typeof imageSource === "string") {
            img.src = imageSource;
        } else {
            img.src = URL.createObjectURL(imageSource);
        }
    });
}

/**
 * Create a solid color image as Uint16Array (RGB565)
 */
export function createSolidColorRGB565(
    color: string,
    width: number,
    height: number
): Uint16Array {
    const rgb565Color = hexToRGB565(color);
    const result = new Uint16Array(width * height);
    result.fill(rgb565Color);
    return result;
}
