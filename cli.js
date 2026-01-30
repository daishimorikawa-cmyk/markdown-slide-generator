#!/usr/bin/env node

import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import OpenAI from "openai";
import { generateSlidePlan } from "./src/plan.js";
import { generateImages } from "./src/images.js";
import { buildPptx } from "./src/pptx.js";

// --- CLI argument parsing ---

function usage() {
  console.log(`
Usage: node cli.js <input.md> [output.pptx] [options]

Arguments:
  input.md          Path to a Markdown file
  output.pptx       Output PPTX path (default: out/presentation.pptx)

Options:
  --headings        Split by Markdown headings instead of AI auto-split
  --size <size>     Image size: 1024x1024 | 1792x1024 | 1024x1792
                    (default: 1024x1024)
  --no-images       Skip image generation entirely
  --help            Show this help message

Environment (.env):
  OPENAI_API_KEY    Required. Your OpenAI API key
  OPENAI_MODEL      Chat model (default: gpt-4.1-mini)
  DALLE_MODEL       Image model (default: dall-e-3)
`);
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const opts = {
    input: null,
    output: "out/presentation.pptx",
    useHeadings: false,
    size: "1024x1024",
    noImages: false,
  };

  const positional = [];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    } else if (arg === "--headings") {
      opts.useHeadings = true;
    } else if (arg === "--size") {
      i++;
      opts.size = args[i];
    } else if (arg === "--no-images") {
      opts.noImages = true;
    } else if (!arg.startsWith("-")) {
      positional.push(arg);
    } else {
      console.error(`Unknown option: ${arg}`);
      usage();
      process.exit(1);
    }
  }

  if (positional.length < 1) {
    console.error("Error: input markdown file is required.");
    usage();
    process.exit(1);
  }

  opts.input = positional[0];
  if (positional[1]) {
    opts.output = positional[1];
  }

  return opts;
}

// --- Main ---

async function main() {
  const opts = parseArgs(process.argv);

  // Validate input
  if (!fs.existsSync(opts.input)) {
    console.error(`Error: File not found: ${opts.input}`);
    process.exit(1);
  }

  // Validate API key
  if (!process.env.OPENAI_API_KEY) {
    console.error(
      "Error: OPENAI_API_KEY is not set. Create a .env file or set the environment variable."
    );
    process.exit(1);
  }

  const openai = new OpenAI();

  // Ensure output directory exists
  const outDir = path.dirname(opts.output);
  fs.mkdirSync(outDir, { recursive: true });

  // Step 1: Read markdown
  console.log(`\n=== Step 1: Reading markdown ===`);
  const markdown = fs.readFileSync(opts.input, "utf-8");
  console.log(`Read ${markdown.length} characters from ${opts.input}`);

  // Step 2: Generate slide plan
  console.log(`\n=== Step 2: Generating slide plan via OpenAI ===`);
  const plan = await generateSlidePlan(openai, markdown, {
    useHeadings: opts.useHeadings,
  });
  console.log(`Generated plan with ${plan.slides.length} slides:`);
  for (const [i, slide] of plan.slides.entries()) {
    console.log(`  [${i + 1}] ${slide.title} (${slide.bullets.length} bullets)`);
  }

  // Step 3: Generate images
  let imagePaths;
  if (opts.noImages) {
    console.log(`\n=== Step 3: Skipping image generation (--no-images) ===`);
    imagePaths = plan.slides.map(() => null);
  } else {
    console.log(`\n=== Step 3: Generating images via DALL·E ===`);
    imagePaths = await generateImages(openai, plan.slides, {
      outDir,
      size: opts.size,
    });
    const successCount = imagePaths.filter(Boolean).length;
    console.log(
      `Generated ${successCount}/${plan.slides.length} images successfully.`
    );
  }

  // Step 4: Build PPTX
  console.log(`\n=== Step 4: Building PPTX ===`);
  await buildPptx(plan.slides, imagePaths, opts.output);

  console.log(`\n✓ Done! Output: ${opts.output}\n`);
}

main().catch((err) => {
  console.error(`\nFatal error: ${err.message}`);
  process.exit(1);
});
