import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
	plugins: [
		react(),
		tailwindcss(),
		viteStaticCopy({
			targets: [
				{
					src: 'public/manifest.json',
					dest: '.',
				}
			],
		}),
	],
	build: {
		outDir: 'build',
		rollupOptions: {
			input: {
				main: './index.html',
				background: 'src/utils/background.ts',
				content: 'src/utils/content.ts',
			},
			output: {
				entryFileNames: ({ name }) => {
					if (name === 'content') return 'content.js';
					if (name === 'background') return 'background.js';
					return 'assets/[name].js';
				},
				assetFileNames: 'assets/[name][extname]'
			},
		},
	},
});
