export {};

declare global {
  interface Window {
    electronAPI: {
      getWikiRoot: () => Promise<string>;
      setWikiRoot: (path: string) => Promise<boolean>;
      selectDirectory: () => Promise<string | null>;
      getWikiTree: () => Promise<any[]>;
      readFile: (path: string) => Promise<string>;
      writeFile: (path: string, content: string) => Promise<boolean>;
      createFile: (parentPath: string, name: string) => Promise<string>;
      renameNode: (oldPath: string, newName: string) => Promise<string>;
      deleteNode: (path: string) => Promise<boolean>;
      moveNode: (srcPath: string, destDir: string) => Promise<string>;
      importObsidianVault: (vaultPath: string, targetCategory?: string) => Promise<{ success: boolean; targetDir: string }>;
      openInExplorer: (path: string) => Promise<void>;
      openWithObsidian: (path: string) => Promise<void>;
      getOllamaModels: () => Promise<{ chatModels: { name: string; size: string }[]; embeddingModels: { name: string; size: string }[] }>;
      platform: string;
    };
  }
}
