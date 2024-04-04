/// <reference types="vite/client" />

interface ImportMetaEnv {
	// Define your environment variables here
	readonly VITE_BACKEND_URL: string;
	// Add other environment variables as needed
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
