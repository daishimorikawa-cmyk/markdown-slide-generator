import { z } from "zod";

// --- Schema ---

const SlideSchema = z.object({
  title: z.string().min(1),
  bullets: z.array(z.string()).min(1).max(7),
  image_prompt: z.string().min(1),
});

const PresentationSchema = z.object({
  slides: z.array(SlideSchema).min(1),
});

export { SlideSchema, PresentationSchema };

// --- Heading-based split mode ---

/**
 * Split markdown by headings (# or ##) into per-slide chunks.
 * Returns an array of { heading, body } objects.
 */
export function splitByHeadings(markdown) {
  const lines = markdown.split("\n");
  const sections = [];
  let current = null;

  for (const line of lines) {
    const m = line.match(/^#{1,2}\s+(.+)/);
    if (m) {
      if (current) sections.push(current);
      current = { heading: m[1].trim(), body: "" };
    } else if (current) {
      current.body += line + "\n";
    }
  }
  if (current) sections.push(current);
  return sections;
}

// --- Main planner ---

const SYSTEM_PROMPT = `You are a presentation designer. Given Markdown content, produce a JSON object that defines slide content for a PowerPoint presentation.

Rules:
- Output ONLY valid JSON, no markdown fences, no explanation.
- The JSON must have a single key "slides" which is an array.
- Each slide object has exactly: "title" (string), "bullets" (array of 3-5 strings), "image_prompt" (string).
- "image_prompt" MUST be in English regardless of the source language. It should describe a high-quality illustration suitable for a business presentation slide.
- Keep bullet points concise (under 20 words each).
- Create 1 slide per major topic/section in the source material.`;

/**
 * Generate slide plan JSON from markdown content using OpenAI Chat Completions.
 *
 * @param {import("openai").default} openai - OpenAI client instance
 * @param {string} markdown - Raw markdown content
 * @param {object} options
 * @param {string} [options.model] - Chat model to use
 * @param {boolean} [options.useHeadings] - Split by headings first
 * @param {number} [options.maxRetries] - Max retries on failure (default 2)
 * @returns {Promise<z.infer<typeof PresentationSchema>>}
 */
export async function generateSlidePlan(openai, markdown, options = {}) {
  const {
    model = process.env.OPENAI_MODEL || "gpt-4.1-mini",
    useHeadings = false,
    maxRetries = 2,
  } = options;

  let userContent;

  if (useHeadings) {
    const sections = splitByHeadings(markdown);
    if (sections.length === 0) {
      throw new Error("No headings found in markdown (useHeadings mode).");
    }
    userContent =
      `The following markdown has been split into ${sections.length} sections by headings. ` +
      `Create exactly ${sections.length} slides, one per section.\n\n` +
      sections
        .map(
          (s, i) =>
            `--- Section ${i + 1}: ${s.heading} ---\n${s.body.trim()}`
        )
        .join("\n\n");
  } else {
    userContent = markdown;
  }

  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await openai.chat.completions.create({
        model,
        temperature: 0.4,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userContent },
        ],
        response_format: { type: "json_object" },
      });

      const raw = response.choices[0].message.content;
      const parsed = JSON.parse(raw);
      const validated = PresentationSchema.parse(parsed);
      return validated;
    } catch (err) {
      lastError = err;
      console.error(
        `[plan] Attempt ${attempt + 1}/${maxRetries + 1} failed: ${err.message}`
      );
      if (attempt < maxRetries) {
        await sleep(1000 * (attempt + 1));
      }
    }
  }

  throw new Error(`Failed to generate slide plan: ${lastError.message}`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
