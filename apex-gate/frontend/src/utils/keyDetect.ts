const KEY_PREFIXES: Array<[string, string]> = [
  ["nvapi-", "nvidia_nim"],
  ["sk-ant-", "anthropic"],
  ["sk-or-", "openrouter"],
  ["gsk_", "groq"],
  ["AIza", "google_gemini"],
  ["hf_", "huggingface"],
  ["r8_", "replicate"],
  ["sk-", "openai"],
];

export function detectProviderSlug(key: string): string | null {
  for (const [prefix, slug] of KEY_PREFIXES) {
    if (key.startsWith(prefix)) return slug;
  }
  return null;
}
