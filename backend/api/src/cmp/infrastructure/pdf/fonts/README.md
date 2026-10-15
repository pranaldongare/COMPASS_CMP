# Fonts for generated PDFs

Noto Sans, from the Noto project (<https://github.com/notofonts>), under the
SIL Open Font License 1.1 (`OFL.txt`). Bundled so a PDF renders the same on
every server: a system font differs per machine, and most servers have no font
for an Indian script at all.

| File | Covers | Languages |
|---|---|---|
| `NotoSans-Regular.ttf`, `NotoSans-Bold.ttf` | Latin, digits, punctuation | English, and every label |
| `NotoSansDevanagari-Regular.ttf` | Devanagari | Hindi, Marathi |
| `NotoSansBengali-Regular.ttf` | Bengali | Bengali |
| `NotoSansGujarati-Regular.ttf` | Gujarati | Gujarati |
| `NotoSansKannada-Regular.ttf` | Kannada | Kannada |
| `NotoSansTamil-Regular.ttf` | Tamil | Tamil |
| `NotoSansTelugu-Regular.ttf` | Telugu | Telugu |

One per `language_code` the platform stores. A language added to that enum
needs its font here, or its text renders as empty boxes. The scripts have a
regular weight only: they appear in notice text, which is never bold.

Fetched 2026-10-15 from `notofonts/notofonts.github.io`, `fonts/<family>/hinted/ttf/`.
