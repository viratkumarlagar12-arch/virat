# short2 — "Saans rokne par ghutan kyon hoti hai?" (breath-hold / CO2)

## Where we are (2026-10-11)
- The creator's CapCut export (`download/raw.mp4`, 46.7 s, 720x1280) came out **fully black** (only audio). Its audio
  has the old CapCut music baked in (loud at 24-37 s), and a false start "ab saans..." at ~32 s.
- Asked for a re-export: 1080p, caption track OFF, music muted. Not received yet.
- The creator asked for a **new voiceover** instead of re-recording. Script (3 writers + judge, fact-checked):
  `vo/script.txt` (Devanagari for TTS), `vo/script_roman.txt` (captions), `vo/script.json` (+ on-screen ideas per
  sentence). Rendered with `editor/scripts/tts.py`, Kokoro v1.0, speed 1.34: hm_omega (male, recommended), hm_psi
  (male), hf_alpha (female); timings + respellings in `vo/vo_kokoro_*.json`. The MP3s were sent to the creator; the
  audio is not in git (regenerate with tts.py or ask the creator to attach the one they picked).
- Waiting on the creator for: (1) which voice (1 = hm_omega, 2 = hm_psi, 3 = hf_alpha, or their own recording),
  (2) visuals: the CapCut re-export, or "graphics only".
- Environment: network access opened (Hugging Face, Wikimedia Commons, NASA images, ElevenLabs reachable).
  Pixabay key goes in as env var `PIXABAY_API_KEY` (a network secret can't carry it: Pixabay wants `?key=`).
  Pexels has paused new API keys.

## Edit plan (agreed in the suggestions round)
- Hook: "Ruko! Abhi saans roko... sirf 10 second." + 10->0 countdown ring, "(baith kar, zor mat lagana)";
  A/B cards "A: Oxygen kam" / "B: CO2 zyada", "jawab end mein"; countdown hits 0 on "par bahar ka raasta band!".
- One visual per sentence: body keeps making CO2 + windpipe gate "BAND"; blood vessel filling with CO2 +
  "CO2 + H2O -> carbonic acid" + pH needle slightly down from 7.4 ("thoda acidic"); re-hook "KAUN?";
  brainstem glow "central chemoreceptors"; signal arrows sensors -> breathing centre -> diaphragm, "SAANS LO!";
  answer: card B lights up, "MAIN TRIGGER = BADHTA CO2" (footnote: oxygen ka bhi role hai, carotid body).
- Calm yellow safety card: no hyperventilation before a breath-hold, never practise breath-holding in water.
- Captions Konark style (bold theme, pop, uppercase, keywords CO2/OXYGEN/ACIDIC/BRAIN/SENSORS/SIGNAL), stop before
  the end card (`captions.until`). Music `documentary` at `volume: 9`. Science Unseen Hindi logo end card with fades
  (CLAUDE.md "Channel end card").
- Optional creator clips: holding breath (cheeks puffed, nose pinched), struggling, gasp; pulse-oximeter shot.
- Title: "Saans Rokne Par Ghutan Kyon Hoti Hai? Asli Wajah CO2 Hai! #shorts". Pinned comment: A ya B question +
  the safety line. Sources: StatPearls (NBK554620), Parkes 2006 "Breath-holding and its breakpoint".
