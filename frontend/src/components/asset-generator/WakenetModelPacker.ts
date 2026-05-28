/**
 * WakenetModelPacker — Browser-side wake word model binary packer
 * Ported from 78/xiaozhi-assets-generator (MIT License)
 *
 * Binary format (srmodels.bin):
 * {
 *   model_num: uint32 LE
 *   model_info_t[] (for each model):
 *     model_name: char[32]
 *     file_number: uint32 LE
 *     file_info[] (for each file):
 *       file_name: char[32]
 *       file_start: uint32 LE
 *       file_len: uint32 LE
 *   model_data[] (raw file data, concatenated)
 * }
 */

export interface WakenetStats {
  modelCount: number;
  fileCount: number;
  totalSize: number;
  models: string[];
}

export class WakenetModelPacker {
  private models = new Map<string, Map<string, ArrayBuffer>>();

  /**
   * Add a model file
   */
  addModelFile(modelName: string, fileName: string, fileData: ArrayBuffer): void {
    if (!this.models.has(modelName)) {
      this.models.set(modelName, new Map());
    }
    this.models.get(modelName)!.set(fileName, fileData);
  }

  /**
   * Load a wakenet/multinet model from the server's static directory
   * @param modelName - e.g. "wn9s_nihaoxiaozhi", "mn6_cn"
   * @param baseStaticUrl - base URL for static assets (default: "./static")
   */
  async loadModelFromShare(modelName: string, baseStaticUrl = "./static"): Promise<boolean> {
    try {
      let modelFiles: string[];
      let baseUrl: string;

      if (modelName.startsWith("wn9")) {
        // WakeNet model
        modelFiles = ["_MODEL_INFO_", "wn9_data", "wn9_index"];
        baseUrl = `${baseStaticUrl}/wakenet_model/${modelName}/`;
      } else if (modelName.startsWith("mn6") || modelName.startsWith("mn7")) {
        // MultiNet model
        const prefix = modelName.substring(0, 3);
        modelFiles = ["_MODEL_INFO_", `${prefix}_data`, `${prefix}_index`, "vocab"];
        baseUrl = `${baseStaticUrl}/multinet_model/${modelName}/`;

        // Also load FST model (required for MultiNet 6/7)
        await this.loadFSTModel(baseStaticUrl);
      } else {
        throw new Error(`Unknown model type: ${modelName}`);
      }

      let loadedFiles = 0;
      for (const fileName of modelFiles) {
        try {
          const response = await fetch(`${baseUrl}${fileName}`);
          if (response.ok) {
            const fileData = await response.arrayBuffer();
            this.addModelFile(modelName, fileName, fileData);
            loadedFiles++;
          } else {
            console.warn(`Cannot load file: ${fileName}, status: ${response.status}`);
          }
        } catch (error) {
          console.warn(`Failed to load file: ${fileName}`, error);
        }
      }

      return loadedFiles === modelFiles.length;
    } catch (error) {
      console.error(`Failed to load model: ${modelName}`, error);
      return false;
    }
  }

  /**
   * Load FST model files (required for MultiNet)
   */
  private async loadFSTModel(baseStaticUrl: string): Promise<boolean> {
    const modelName = "fst";
    if (this.models.has(modelName)) return true;

    const modelFiles = ["commands_cn.txt", "commands_en.txt"];
    const baseUrl = `${baseStaticUrl}/multinet_model/fst/`;

    let loadedFiles = 0;
    for (const fileName of modelFiles) {
      try {
        const response = await fetch(`${baseUrl}${fileName}`);
        if (response.ok) {
          const fileData = await response.arrayBuffer();
          this.addModelFile(modelName, fileName, fileData);
          loadedFiles++;
        }
      } catch (error) {
        console.warn(`Failed to load FST file: ${fileName}`, error);
      }
    }
    return loadedFiles > 0;
  }

  /** Pack string into fixed-length binary (ASCII, null-padded) */
  private packString(str: string, maxLen: number): Uint8Array {
    const bytes = new Uint8Array(maxLen);
    const copyLen = Math.min(str.length, maxLen);
    for (let i = 0; i < copyLen; i++) {
      bytes[i] = str.charCodeAt(i) & 0xff;
    }
    return bytes;
  }

  /** Pack uint32 as little-endian */
  private packUint32(value: number): Uint8Array {
    const bytes = new Uint8Array(4);
    bytes[0] = value & 0xff;
    bytes[1] = (value >> 8) & 0xff;
    bytes[2] = (value >> 16) & 0xff;
    bytes[3] = (value >> 24) & 0xff;
    return bytes;
  }

  /**
   * Pack all loaded models into srmodels.bin format
   */
  packModels(): ArrayBuffer {
    if (this.models.size === 0) {
      throw new Error("No model data to pack");
    }

    // Sort models by name for deterministic output
    const modelDataList: Array<{
      name: string;
      files: Array<[string, ArrayBuffer]>;
    }> = [];

    for (const [modelName, files] of Array.from(this.models.entries()).sort((a, b) => a[0].localeCompare(b[0]))) {
      const sortedFiles = Array.from(files.entries()).sort((a, b) => a[0].localeCompare(b[0]));
      modelDataList.push({ name: modelName, files: sortedFiles });
    }

    // Calculate header length
    const modelNum = this.models.size;
    let headerLen = 4; // model_num

    for (const model of modelDataList) {
      headerLen += 32 + 4; // model_name + file_number
      headerLen += model.files.length * (32 + 4 + 4); // per file: name + start + len
    }

    // Calculate total size
    let totalDataSize = 0;
    for (const files of this.models.values()) {
      for (const fileData of files.values()) {
        totalDataSize += fileData.byteLength;
      }
    }

    const totalSize = headerLen + totalDataSize;
    const output = new Uint8Array(totalSize);
    let offset = 0;

    // Write model count
    output.set(this.packUint32(modelNum), offset);
    offset += 4;

    // Write model info headers
    let dataOffset = headerLen;

    for (const model of modelDataList) {
      // Model name (32 bytes)
      output.set(this.packString(model.name, 32), offset);
      offset += 32;

      // File count
      output.set(this.packUint32(model.files.length), offset);
      offset += 4;

      // File info entries
      for (const [fileName, fileData] of model.files) {
        output.set(this.packString(fileName, 32), offset);
        offset += 32;
        output.set(this.packUint32(dataOffset), offset);
        offset += 4;
        output.set(this.packUint32(fileData.byteLength), offset);
        offset += 4;
        dataOffset += fileData.byteLength;
      }
    }

    // Write file data
    for (const model of modelDataList) {
      for (const [, fileData] of model.files) {
        output.set(new Uint8Array(fileData), offset);
        offset += fileData.byteLength;
      }
    }

    return output.buffer;
  }

  /**
   * Validate model compatibility with chip
   */
  static isValidModel(modelName: string, chipModel: string): boolean {
    const isC3OrC6 = chipModel === "esp32c3" || chipModel === "esp32c6";
    return isC3OrC6 ? modelName.startsWith("wn9s_") : modelName.startsWith("wn9_");
  }

  /** Clear all loaded models */
  clear(): void {
    this.models.clear();
  }

  /** Get stats about loaded models */
  getStats(): WakenetStats {
    let totalFiles = 0;
    let totalSize = 0;

    for (const files of this.models.values()) {
      totalFiles += files.size;
      for (const fileData of files.values()) {
        totalSize += fileData.byteLength;
      }
    }

    return {
      modelCount: this.models.size,
      fileCount: totalFiles,
      totalSize,
      models: Array.from(this.models.keys()),
    };
  }
}
