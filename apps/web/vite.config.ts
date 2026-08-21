import { fileURLToPath, URL } from 'node:url'
import { config } from '@en/config'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'
import viteCompression from 'vite-plugin-compression'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vite.dev/config/
export default defineConfig({
  // 部署在 /en/ 子路径下，导航页在 /
  base: '/en/',
  server: {
    port: config.ports.web,
    proxy: {
      '/api': {
        target: `http://localhost:${config.ports.server}`,
        changeOrigin: true,
      },
      '/ai': {
        target: `http://localhost:${config.ports.ai}`,
        changeOrigin: true,
      },
    },
  },
  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss(),
    // Element Plus 按需导入
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
    // Gzip 压缩
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 1024, // 大于 1KB 就压缩
      deleteOriginFile: false,
    }),
    // Brotli 压缩（压缩率更高）
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 1024,
      deleteOriginFile: false,
    }),
    // Bundle 分析（构建时生成 stats.html）
    visualizer({
      filename: 'dist/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // chunk 大小警告阈值
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        // 手动分包策略（函数式，兼容 TypeScript）
        manualChunks(id: string) {
          if (id.includes('node_modules')) {
            // Vue 生态
            if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) {
              return 'vendor-vue'
            }
            // Element Plus UI
            if (id.includes('element-plus') || id.includes('@element-plus')) {
              return 'vendor-element'
            }
            // Three.js 3D 引擎
            if (id.includes('three')) {
              return 'vendor-three'
            }
            // GSAP 动画库
            if (id.includes('gsap')) {
              return 'vendor-gsap'
            }
            // Socket.IO
            if (id.includes('socket.io')) {
              return 'vendor-socket'
            }
            // 其他工具库
            if (id.includes('axios') || id.includes('marked') || id.includes('dayjs')) {
              return 'vendor-utils'
            }
            // 剩余 node_modules
            return 'vendor-common'
          }
        },
        // 资源文件命名
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo: any) => {
          const name = assetInfo.name || ''
          if (/\.(png|jpe?g|gif|svg|webp|avif)$/i.test(name)) {
            return 'assets/images/[name]-[hash][extname]'
          }
          if (/\.(woff2?|eot|ttf|otf)$/i.test(name)) {
            return 'assets/fonts/[name]-[hash][extname]'
          }
          if (/\.css$/i.test(name)) {
            return 'assets/css/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        },
      },
    },
    // esbuild 压缩（比 Terser 快 10-100 倍，适合低配服务器构建）
    minify: 'esbuild',
    // 启用 sourcemap（仅生产环境需要排查问题时开启）
    sourcemap: false,
  },
  // CSS 处理
  css: {
    devSourcemap: true,
  },
})
