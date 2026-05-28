/**
 * SpiffsGenerator — Browser-side SPIFFS binary generator
 * Ported from 78/xiaozhi-assets-generator (MIT License)
 * 
 * Binary format:
 * {
 *   total_files: uint32 LE          // File count
 *   checksum: uint32 LE             // Data checksum
 *   combined_data_length: uint32 LE // Total data length
 *   mmap_table: [                   // File mapping table
 *     {
 *       name: char[32]              // Filename (32 bytes, null-padded)
 *       size: uint32 LE             // File size
 *       offset: uint32 LE           // File offset in data section
 *       width: uint16 LE            // Image width (0 if N/A)
 *       height: uint16 LE           // Image height (0 if N/A)
 *     }
 *   ]
 *   file_data: [                    // File data section
 *     0x5A 0x5A + file_data         // Each file prefixed with 0x5A5A marker
 *   ]
 * }
 */

export interface SpiffsFile {
  filename: string;
  data: ArrayBuffer;
  size: number;
  width: number;
  height: number;
}

export interface SpiffsStats {
  fileCount: number;
  totalSize: number;
  fileTypes: Record<string, number>;
  averageFileSize: number;
}

export type ProgressCallback = (progress: number, message: string) => void;

export class SpiffsGenerator {
  private files: SpiffsFile[] = [];
  private textEncoder = new TextEncoder();

  /**
   * Add a file to the SPIFFS image
   */
  addFile(filename: string, data: ArrayBuffer, options: { width?: number; height?: number } = {}): void {
    if (filename.length > 32) {
      console.warn(`Filename "${filename}" exceeds 32 bytes and will be truncated`);
    }
    this.files.push({
      filename,
      data,
      size: data.byteLength,
      width: options.width || 0,
      height: options.height || 0,
    });
  }

  /**
   * Get image dimensions from image data using browser Image API
   */
  async getImageDimensions(imageData: ArrayBuffer): Promise<{ width: number; height: number }> {
    return new Promise((resolve) => {
      try {
        const blob = new Blob([imageData]);
        const url = URL.createObjectURL(blob);
        const img = new Image();

        img.onload = () => {
          URL.revokeObjectURL(url);
          resolve({ width: img.width, height: img.height });
        };

        img.onerror = () => {
          URL.revokeObjectURL(url);
          resolve({ width: 0, height: 0 });
        };

        img.src = url;
      } catch {
        resolve({ width: 0, height: 0 });
      }
    });
  }

  /**
   * Parse special image format headers (.sjpg, .spng, .sqoi)
   */
  parseSpecialImageFormat(_filename: string, data: ArrayBuffer): { width: number; height: number } {
    const ext = _filename.toLowerCase().split(".").pop();
    if (ext && ["sjpg", "spng", "sqoi"].includes(ext)) {
      try {
        const view = new DataView(data);
        const width = view.getUint16(14, true); // Little-endian
        const height = view.getUint16(16, true);
        return { width, height };
      } catch (error) {
        console.warn(`Failed to parse special image format: ${_filename}`, error);
      }
    }
    return { width: 0, height: 0 };
  }

  /** Pack uint32 as little-endian bytes */
  private packUint32(value: number): Uint8Array {
    const bytes = new Uint8Array(4);
    bytes[0] = value & 0xff;
    bytes[1] = (value >> 8) & 0xff;
    bytes[2] = (value >> 16) & 0xff;
    bytes[3] = (value >> 24) & 0xff;
    return bytes;
  }

  /** Pack uint16 as little-endian bytes */
  private packUint16(value: number): Uint8Array {
    const bytes = new Uint8Array(2);
    bytes[0] = value & 0xff;
    bytes[1] = (value >> 8) & 0xff;
    return bytes;
  }

  /** Pack string into fixed-length binary (null-padded) */
  private packString(str: string, maxLen: number): Uint8Array {
    const bytes = new Uint8Array(maxLen);
    const encoded = this.textEncoder.encode(str);
    const copyLen = Math.min(encoded.length, maxLen);
    bytes.set(encoded.slice(0, copyLen), 0);
    return bytes;
  }

  /** Compute 16-bit checksum */
  private computeChecksum(data: Uint8Array): number {
    let checksum = 0;
    for (let i = 0; i < data.length; i++) {
      checksum += data[i];
    }
    return checksum & 0xffff;
  }

  /** Sort files by extension then name */
  private sortFiles(files: SpiffsFile[]): SpiffsFile[] {
    return files.slice().sort((a, b) => {
      const extA = a.filename.split(".").pop() || "";
      const extB = b.filename.split(".").pop() || "";
      if (extA !== extB) return extA.localeCompare(extB);
      const nameA = a.filename.replace(/\.[^/.]+$/, "");
      const nameB = b.filename.replace(/\.[^/.]+$/, "");
      return nameA.localeCompare(nameB);
    });
  }

  /**
   * Generate the final assets.bin binary
   */
  async generate(progressCallback?: ProgressCallback): Promise<ArrayBuffer> {
    if (this.files.length === 0) {
      throw new Error("No files to package");
    }

    progressCallback?.(0, "Starting to package files...");

    // Sort files
    const sortedFiles = this.sortFiles(this.files);
    const totalFiles = sortedFiles.length;

    // Process file info and get image dimensions
    interface FileInfo {
      filename: string;
      data: ArrayBuffer;
      size: number;
      offset: number;
      width: number;
      height: number;
    }

    const fileInfoList: FileInfo[] = [];
    let mergedDataSize = 0;

    for (let i = 0; i < sortedFiles.length; i++) {
      const file = sortedFiles[i];
      let width = file.width;
      let height = file.height;

      progressCallback?.(10 + (i / totalFiles) * 30, `Processing file: ${file.filename}`);

      // Auto-detect image dimensions if not provided
      if (width === 0 && height === 0) {
        const specialDims = this.parseSpecialImageFormat(file.filename, file.data);
        if (specialDims.width > 0 || specialDims.height > 0) {
          width = specialDims.width;
          height = specialDims.height;
        } else {
          const ext = file.filename.toLowerCase().split(".").pop();
          if (ext && ["png", "jpg", "jpeg", "gif", "bmp", "webp"].includes(ext)) {
            const dims = await this.getImageDimensions(file.data);
            width = dims.width;
            height = dims.height;
          }
        }
      }

      fileInfoList.push({
        filename: file.filename,
        data: file.data,
        size: file.size,
        offset: mergedDataSize,
        width,
        height,
      });

      mergedDataSize += 2 + file.size; // 2-byte prefix + file data
    }

    progressCallback?.(40, "Building file mapping table...");

    // Build mmap table: name(32) + size(4) + offset(4) + width(2) + height(2) = 44 bytes per entry
    const ENTRY_SIZE = 32 + 4 + 4 + 2 + 2;
    const mmapTableSize = totalFiles * ENTRY_SIZE;
    const mmapTable = new Uint8Array(mmapTableSize);
    let mmapOffset = 0;

    for (const fi of fileInfoList) {
      mmapTable.set(this.packString(fi.filename, 32), mmapOffset);
      mmapOffset += 32;
      mmapTable.set(this.packUint32(fi.size), mmapOffset);
      mmapOffset += 4;
      mmapTable.set(this.packUint32(fi.offset), mmapOffset);
      mmapOffset += 4;
      mmapTable.set(this.packUint16(fi.width), mmapOffset);
      mmapOffset += 2;
      mmapTable.set(this.packUint16(fi.height), mmapOffset);
      mmapOffset += 2;
    }

    progressCallback?.(60, "Merging file data...");

    // Merge file data with 0x5A5A prefix markers
    const mergedData = new Uint8Array(mergedDataSize);
    let mergedOffset = 0;

    for (let i = 0; i < fileInfoList.length; i++) {
      const fi = fileInfoList[i];
      progressCallback?.(60 + (i / totalFiles) * 20, `Merging file: ${fi.filename}`);

      mergedData[mergedOffset] = 0x5a;
      mergedData[mergedOffset + 1] = 0x5a;
      mergedOffset += 2;

      mergedData.set(new Uint8Array(fi.data), mergedOffset);
      mergedOffset += fi.size;
    }

    progressCallback?.(80, "Computing checksum...");

    // Combine mmap table + merged data for checksum
    const combinedData = new Uint8Array(mmapTableSize + mergedDataSize);
    combinedData.set(mmapTable, 0);
    combinedData.set(mergedData, mmapTableSize);

    const checksum = this.computeChecksum(combinedData);
    const combinedDataLength = combinedData.length;

    progressCallback?.(90, "Building final file...");

    // Build final output: header(12) + combined data
    const headerSize = 4 + 4 + 4;
    const totalSize = headerSize + combinedDataLength;
    const finalData = new Uint8Array(totalSize);
    let offset = 0;

    // total_files
    finalData.set(this.packUint32(totalFiles), offset);
    offset += 4;
    // checksum
    finalData.set(this.packUint32(checksum), offset);
    offset += 4;
    // combined_data_length
    finalData.set(this.packUint32(combinedDataLength), offset);
    offset += 4;
    // combined data (mmap + files)
    finalData.set(combinedData, offset);

    progressCallback?.(100, "Packaging completed");
    return finalData.buffer;
  }

  /** Get file statistics */
  getStats(): SpiffsStats {
    let totalSize = 0;
    const fileTypes = new Map<string, number>();

    for (const file of this.files) {
      totalSize += file.size;
      const ext = file.filename.split(".").pop()?.toLowerCase() || "unknown";
      fileTypes.set(ext, (fileTypes.get(ext) || 0) + 1);
    }

    return {
      fileCount: this.files.length,
      totalSize,
      fileTypes: Object.fromEntries(fileTypes),
      averageFileSize: this.files.length > 0 ? Math.round(totalSize / this.files.length) : 0,
    };
  }

  /** Clear all files */
  clear(): void {
    this.files = [];
  }
}
