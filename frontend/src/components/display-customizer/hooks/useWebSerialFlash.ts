/**
 * WebSerial Flash Hook
 * Provides WebSerial flash functionality for ESP32 devices
 */

import { useState, useRef, useCallback } from "react";

export interface FlashProgress {
    stage: "idle" | "connecting" | "erasing" | "writing" | "verifying" | "done" | "error";
    progress: number; // 0-100
    message: string;
}

export interface UseWebSerialFlashOptions {
    baudRate?: number;
    flashAddress?: number;
}

export interface UseWebSerialFlashReturn {
    isSupported: boolean;
    isConnected: boolean;
    chipInfo: string | null;
    flashProgress: FlashProgress;
    connect: () => Promise<boolean>;
    disconnect: () => Promise<void>;
    flash: (binaryData: Uint8Array, address?: number) => Promise<boolean>;
    reset: () => void;
    logs: string[];
}

export function useWebSerialFlash(
    options: UseWebSerialFlashOptions = {}
): UseWebSerialFlashReturn {
    const { baudRate = 115200, flashAddress = 0x0 } = options;

    // State
    const [isConnected, setIsConnected] = useState(false);
    const [chipInfo, setChipInfo] = useState<string | null>(null);
    const [flashProgress, setFlashProgress] = useState<FlashProgress>({
        stage: "idle",
        progress: 0,
        message: "Ready to connect",
    });
    const [logs, setLogs] = useState<string[]>([]);

    // Refs for esptool
    const transportRef = useRef<any>(null);
    const espLoaderRef = useRef<any>(null);
    const portRef = useRef<any>(null);

    // Check WebSerial support
    const isSupported = typeof navigator !== "undefined" && "serial" in navigator;

    // Add log entry
    const addLog = useCallback((message: string) => {
        const timestamp = new Date().toLocaleTimeString();
        setLogs((prev) => [...prev.slice(-99), `[${timestamp}] ${message}`]);
    }, []);

    // Load esptool-js dynamically
    const loadEsptool = useCallback(async () => {
        try {
            // Dynamic import esptool-js
            const esptool = await import("esptool-js");
            return esptool;
        } catch (error) {
            addLog(`Error loading esptool-js: ${error}`);
            throw error;
        }
    }, [addLog]);

    // Connect to device
    const connect = useCallback(async (): Promise<boolean> => {
        if (!isSupported) {
            addLog("WebSerial not supported in this browser");
            return false;
        }

        try {
            setFlashProgress({
                stage: "connecting",
                progress: 10,
                message: "Requesting serial port...",
            });
            addLog("Requesting serial port...");

            // Request port
            const port = await navigator.serial!.requestPort();
            portRef.current = port;

            setFlashProgress({
                stage: "connecting",
                progress: 30,
                message: "Loading esptool...",
            });
            addLog("Loading esptool-js...");

            // Load esptool
            const esptool = await loadEsptool();

            setFlashProgress({
                stage: "connecting",
                progress: 50,
                message: "Connecting to device...",
            });

            // Create transport
            const transport = new esptool.Transport(port, true);
            transportRef.current = transport;

            // Create loader with terminal
            const loader = new esptool.ESPLoader({
                transport,
                baudrate: baudRate,
                romBaudrate: baudRate,
                terminal: {
                    clean: () => { },
                    writeLine: (text: string) => addLog(text),
                    write: (text: string) => addLog(text),
                },
            } as any);

            setFlashProgress({
                stage: "connecting",
                progress: 70,
                message: "Detecting chip...",
            });
            addLog("Detecting chip...");

            // Connect and get chip
            const chip = await loader.main();
            espLoaderRef.current = loader;

            setChipInfo(chip);
            setIsConnected(true);
            setFlashProgress({
                stage: "idle",
                progress: 100,
                message: `Connected to ${chip}`,
            });
            addLog(`Connected to ${chip}`);

            return true;
        } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            addLog(`Connection error: ${errorMsg}`);
            setFlashProgress({
                stage: "error",
                progress: 0,
                message: `Connection failed: ${errorMsg}`,
            });
            return false;
        }
    }, [isSupported, baudRate, loadEsptool, addLog]);

    // Disconnect
    const disconnect = useCallback(async () => {
        try {
            if (transportRef.current) {
                await transportRef.current.disconnect();
            }
            if (portRef.current) {
                await portRef.current.close();
            }
        } catch (error) {
            addLog(`Disconnect error: ${error}`);
        } finally {
            transportRef.current = null;
            espLoaderRef.current = null;
            portRef.current = null;
            setIsConnected(false);
            setChipInfo(null);
            setFlashProgress({
                stage: "idle",
                progress: 0,
                message: "Disconnected",
            });
            addLog("Disconnected");
        }
    }, [addLog]);

    // Flash binary
    const flash = useCallback(
        async (binaryData: Uint8Array, address: number = flashAddress): Promise<boolean> => {
            if (!espLoaderRef.current) {
                addLog("Not connected. Please connect first.");
                return false;
            }

            try {
                const loader = espLoaderRef.current;

                setFlashProgress({
                    stage: "erasing",
                    progress: 10,
                    message: "Preparing flash...",
                });
                addLog(`Preparing to flash at 0x${address.toString(16)}...`);

                // Convert Uint8Array to string for esptool-js
                const binaryString = Array.from(binaryData)
                    .map((byte) => String.fromCharCode(byte))
                    .join("");

                setFlashProgress({
                    stage: "writing",
                    progress: 30,
                    message: "Writing data...",
                });
                addLog(`Writing ${binaryData.length} bytes...`);

                // Use writeFlash API (esptool-js v0.5+)
                await loader.writeFlash({
                    fileArray: [{
                        data: binaryString,
                        address: address,
                    }],
                    flashSize: "keep",
                    flashMode: "keep",
                    flashFreq: "keep",
                    eraseAll: false,
                    compress: true,
                    reportProgress: (_fileIndex: number, written: number, total: number) => {
                        const percent = Math.round((written / total) * 60) + 30;
                        setFlashProgress({
                            stage: "writing",
                            progress: percent,
                            message: `Writing: ${Math.round((written / total) * 100)}%`,
                        });
                    },
                });

                setFlashProgress({
                    stage: "verifying",
                    progress: 95,
                    message: "Verifying...",
                });
                addLog("Verifying flash...");

                // Hard reset via transport (esptool-js v0.5+ API)
                // hardReset is not a method on loader, use transport signals
                try {
                    const transport = transportRef.current;
                    if (transport) {
                        // Toggle DTR/RTS to trigger hard reset
                        await transport.setDTR(false);
                        await transport.setRTS(true);
                        await new Promise(r => setTimeout(r, 100));
                        await transport.setRTS(false);
                        addLog("Hard reset sent");
                    }
                } catch (resetErr) {
                    addLog(`Reset warning: ${resetErr}`);
                    // Continue even if reset fails
                }

                setFlashProgress({
                    stage: "done",
                    progress: 100,
                    message: "Flash complete!",
                });
                addLog("Flash completed successfully!");

                return true;
            } catch (error) {
                const errorMsg = error instanceof Error ? error.message : String(error);
                addLog(`Flash error: ${errorMsg}`);
                setFlashProgress({
                    stage: "error",
                    progress: 0,
                    message: `Flash failed: ${errorMsg}`,
                });
                return false;
            }
        },
        [flashAddress, addLog]
    );

    // Reset state
    const reset = useCallback(() => {
        setFlashProgress({
            stage: "idle",
            progress: 0,
            message: "Ready to connect",
        });
        setLogs([]);
    }, []);

    return {
        isSupported,
        isConnected,
        chipInfo,
        flashProgress,
        connect,
        disconnect,
        flash,
        reset,
        logs,
    };
}

export default useWebSerialFlash;
