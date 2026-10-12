# short3 — "Leh mein dal kyun nahi galti?" (why dal is slow to cook in Leh)

Idea from the creator (2026-10-12). Status: script verified + voiceover samples made; waiting for the creator's choices.

## Decisions to remember
- Title wording: the creator's own title says "nahi galti", but dal DOES soften at ~88 C, only several times slower in an open pot
  ("dal kabhi nahi galti" is an overclaim). Use "itni der se kyun galti hai" / "ubalti hai, phir bhi der se galti hai". Never say
  "kabhi nahi", "raw", or any "x guna / minutes" figure on screen (the 2-3x is a model estimate, low confidence).
- Say "khuli deg / open pot" on screen where the 88 C limit is shown. Main cause = air pressure; oxygen (still ~21 % of the air) and
  cold air do not set the boiling point. Hard water, old dal and acid are real but secondary.
- Cooker at Leh: about 114 C (1 kgf/cm2 gauge; 108 C for a 10 psi-type), vs ~120 C at sea level. Never show 120/121 as the Leh number.
  Needs "kuch extra time" (extension rules extrapolate to roughly +45-50 %, medium confidence): no percentage on screen.
  Safety line: open the cooker only when the pressure is fully out; never show a hand on the valve.
- Card C and the answer chip should read "HAWA KA PRESSURE KAM" (plain "pressure kam" could be heard as cooker/blood pressure).
- Search data (vidIQ, India): the topic itself is tiny (<750/month) so it is a feed-curiosity video; "ladakh" 92K, "ladakh road trip" 35K,
  "leh" 22K, "how pressure cooker works" 13.9K (+44 %). Put Ladakh/pressure-cooker words in tags/description, keep numbers tied to "Leh".

## Verified numbers (re-checked with IAPWS-IF97 on 2026-10-12)
Leh town 3,524 m (about 3,500 m) · pressure 65.6 kPa = 64.7 % of sea level (measured 66 %) · water boils 88.2 C (range 87-89) ·
~1 C per 300 m · Everest summit ~70 C · cooker at Leh 114 C · oxygen fraction ~21 % at any altitude.
Sources: Wikipedia Leh / Boiling point / High-altitude cooking / Pressure cooking; Apte 2004 (measured Leh pressure, ijpp.com);
NIST WebBook; CSU Extension (pulses + pressure cooking at altitude); Hawkins (cooker temperature + safety); PubMed 41046567,
7576160 (pectin and softening); Varoquaux 1995 (lentil activation energy); NZ physics note on room-temperature boiling in a syringe.

## Files
- `vo/script.json` (final sentences = TTS segments, each with `on_screen` and `pause_after`), `vo/script.txt` (Devanagari),
  `vo/script_roman.txt` (captions), `vo/script_tts.txt` (same, with "एंड" respelled "एण्ड" for hm_omega), `script_readable.md`.
- Render: `.venv/bin/python editor/scripts/tts.py kokoro:hm_omega projects/short3/vo/script_tts.txt out.wav --speed 1.34
  --pauses "$(cat projects/short3/vo/pauses.json)" --json out.json` -> 38.4 s (hf_alpha 39.1 s). With hm_psi use "जवाब आख़िर में।".
- Plan hints: word_text on the FIRST word of each spoken number ("साढ़े" -> "3,500", "एक" -> "115", "अट्ठासी" -> "88") and put the other
  words of the phrase in captions.hide_words; captions.until before the end card; music `documentary`, volume 9; fade overlays + logo
  end card as in CLAUDE.md. 21 % is shown on screen only (not spoken).

## Voice caveat (the creator must listen)
Free Kokoro voices speak the script clearly (speech-recognition mismatch ~11-13 %), but the recognizer garbles every spoken number,
so the three number moments could not be machine-verified: "साढ़े तीन हज़ार" (~7 s), "अट्ठासी डिग्री" (~17 s), "एक सौ पंद्रह" (~32 s).
The numbers are shown on screen too. Better options: the creator records it, or vidIQ ElevenLabs (~14 credits per ~1000 characters,
creator had 139 credits; ask first).

## Open questions for the creator
1. Voice: hm_omega / hf_alpha / own recording / ElevenLabs?
2. Real footage (Leh, dal, pressure cooker)? Otherwise everything is generated graphics (mountain + altitude meter, pressure bars,
   thermometer stuck at 88, boiling pot, cooker cutaway, A/B/C cards).
3. Safe room-temperature-boiling syringe demo is possible to film (small 20 mL plastic syringe, no needle, ~5 mL lukewarm water).
