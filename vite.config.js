import { defineConfig } from 'vite';
export default defineConfig({base:'./',build:{outDir:'docs',emptyOutDir:true,chunkSizeWarningLimit:900},server:{host:'127.0.0.1'}});
