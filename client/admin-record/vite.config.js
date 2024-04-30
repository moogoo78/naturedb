import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vitejs.dev/config/
// top-level-await error: https://stackoverflow.com/a/75839023
export default defineConfig({
  plugins: [svelte()],
  esbuild: {
    supported: {
      'top-level-await': true //browsers can handle top-level-await features
    },
  },
  build: {
    //outDir: '../../app/blueprints/admin_static/record-form',
    outDir: 'dist',
    assetsDir: 'admin/assets',
  }
})
