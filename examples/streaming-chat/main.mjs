/**
 * Streaming chat example for ModelBridge.
 *
 * Setup:
 *   export MODELBRIDGE_URL=http://localhost:8000
 *   export MODELBRIDGE_API_KEY=mb_your_key
 *
 * Run:
 *   cd ../../packages/typescript-sdk && npm install && npm run build
 *   node main.mjs
 */

import { ModelBridge } from "../../packages/typescript-sdk/dist/index.js";

const client = new ModelBridge({
  baseURL: process.env.MODELBRIDGE_URL || "http://localhost:8000",
  apiKey: process.env.MODELBRIDGE_API_KEY,
});

for await (const chunk of client.chat.completions.stream({
  model: "auto",
  messages: [{ role: "user", content: "Count from 1 to 5 briefly." }],
})) {
  const delta = chunk.choices?.[0]?.delta?.content;
  if (delta) process.stdout.write(delta);
}
console.log();
