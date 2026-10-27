import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';
import path from 'path';
import fs from 'fs';

function copyToUiHtmlPlugin() {
  return {
    name: 'copy-to-ui-html',
    closeBundle() {
      const distIndex = path.resolve(__dirname, 'dist/index.html');
      const targetUi = path.resolve(__dirname, '../api/ui.html');
      if (fs.existsSync(distIndex)) {
        fs.copyFileSync(distIndex, targetUi);
        console.log(`[build] Successfully updated ${targetUi}`);
      }
    }
  };
}

export default defineConfig({
  plugins: [viteSingleFile(), copyToUiHtmlPlugin()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
});
