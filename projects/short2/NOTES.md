# short2 — "Saans rokne par ghutan kyon hoti hai?" (breath-hold / CO2)

## Where we are (2026-10-11)
- **v1 rendered.** Voice = the creator's own ElevenLabs take of `vo/script.txt` (voice "Bunty – Friendly Fun",
  speed 0.95, stability 60, similarity 30, v4; 48.7 s), sent in chat → `vo/elevenlabs_bunty.mp3` (not in git).
  Tightened with `tighten_vo.py vo_work tight/voice48k.wav --max-pause 0.12` → 46.5 s, all 118 words kept.
- Picture = the creator's CapCut re-export (`download/reexport.mp4`, 1080x1920, 46.7 s, AI anatomy shots in script
  order, no speech in its audio — dropped) re-timed to the voice with `assemble.py edl.json assembled.mp4`, plus
  Pixabay clips for the safety line (`media/pixabay_61292.mp4` breathing man, `pixabay_34283.mp4` pool dip lands on
  "paani", `pixabay_37712.mp4` deep water for "behoshi"). Logo end card = the export's last 0.6 s at speed 0.3 (a still).
- Earlier: the first CapCut export was fully black; Kokoro voices (hm_omega/hm_psi/hf_alpha, `vo/vo_kokoro_*.json`) were
  offered but the creator made their own ElevenLabs voice instead.
- Environment: Pixabay works. The `PIXABAY_API_KEY` value has extra pasted text around the key ("Your … key …");
  `pixabay.py` extracts the key, but the creator should set the value to just the key.

## Edit (plan.json)
- Hook: "RUKO! ✋ ABHI SAANS ROKO" on the chest + a corner 10-s timer that hits 0 on "band" (red, "Ab saans lo").
- A/B cards (Oxygen kam / CO2 zyada) + "JAWAB END MEIN 🔒" stamp; CO2 card; ring "BAHAR KA RAASTA" + "BAND!" stamp
  on the windpipe; Carbonic acid / thoda acidic cards; "KAUN? 🤔" slam; brainstem ring + sensors card (central
  chemoreceptors); SIGNAL chain Sensors → Breathing centre → Diaphragm; "SAANS LO!" slam; CO2/urge bars; "YAHI THI
  WOH BECHAINI"; answer reveal (A dimmed, B green ✅); MAIN TRIGGER list; calm yellow safety list + Behoshi card;
  A/B + "COMMENT KARO 💬" CTA; dip to black → logo, fade out.
- Captions pop, uppercase, Konark style, stop at 46.45. Music `documentary` volume 9.
- Title: "Saans Rokne Par Ghutan Kyon Hoti Hai? Asli Wajah CO2 Hai! #shorts". Pinned comment: A ya B question +
  safety line + "oxygen ka bhi role hai (carotid body), par main trigger CO2". Sources: StatPearls (NBK554620),
  Parkes 2006 "Breath-holding and its breakpoint".
