/**
 * Language names, in the language itself.
 *
 * "हिन्दी", not "Hindi". Somebody choosing a language they can read should not
 * have to read English to find it — which is the whole point of offering the
 * choice.
 */
export const LANGUAGE_NAMES: Record<string, string> = {
  english: "English",
  hindi: "हिन्दी",
  bengali: "বাংলা",
  marathi: "मराठी",
  telugu: "తెలుగు",
  tamil: "தமிழ்",
  gujarati: "ગુજરાતી",
  kannada: "ಕನ್ನಡ",
};

/**
 * The BCP 47 tag for each, for `lang=`. A screen reader reads Hindi text with
 * an English voice unless the markup says otherwise, and a browser picks the
 * wrong font and hyphenation (review UX-4).
 */
export const LANGUAGE_TAGS: Record<string, string> = {
  english: "en",
  hindi: "hi",
  bengali: "bn",
  marathi: "mr",
  telugu: "te",
  tamil: "ta",
  gujarati: "gu",
  kannada: "kn",
};

export function langTag(code: string | null | undefined): string | undefined {
  return code ? LANGUAGE_TAGS[code] : undefined;
}
