#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Read the video data to get the username
const dataPath = path.join(__dirname, 'src', 'video-data.json');
const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));

const username = data.meta?.username || 'unknown';
const timestamp = Math.floor(Date.now() / 1000);

const outputFilename = `wrapped-2025-${username}-${timestamp}.mp4`;
const outputPath = path.join('out', outputFilename);

console.log(`Rendering video for @${username}...`);
console.log(`Output: ${outputPath}`);

// Ensure out directory exists
const outDir = path.join(__dirname, 'out');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// Run the remotion render command
const command = `npx remotion render src/index.ts WrappedVideo "${outputPath}"`;

try {
  execSync(command, { stdio: 'inherit', cwd: __dirname });
  console.log(`\nVideo saved to: ${outputPath}`);
} catch (error) {
  console.error('Render failed:', error.message);
  process.exit(1);
}
