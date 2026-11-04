export type ImportFile = { batchId: string; file: File };
export type ImportSource = {
  importFile: ImportFile | null;
  setImportFile(file: ImportFile | null): void;
};
