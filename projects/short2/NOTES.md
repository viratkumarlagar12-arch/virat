# short2 — "Saans rokne par ghutan kyon hoti hai?" (breath-hold / CO2)

## Where we are (2026-10-11)
- **v2 rendered** (creator: "fix scenes/visuals as you think, add/delete clips, edit like a pro"). v1 → v2 was planned
  from a 3-lens critique (pacing, visual storytelling, graphics/sound/facts) + 6 Pixabay scouts, then QA'd by
  independent reviewers.
- Voice = the creator's ElevenLabs take of `vo/script.txt` (voice "Bunty – Friendly Fun", speed 0.95, stability 60,
  similarity 30, v4; 48.7 s) → `vo/elevenlabs_bunty.mp3` (not in git), tightened with
  `tighten_vo.py vo_work tight/voice48k.wav --max-pause 0.12` → 46.5 s, all 118 words kept.
- Picture source: the creator's CapCut re-export `download/reexport.mp4` (1080x1920, AI anatomy shots; it is 24p in a
  30 fps file, so never slow a MOVING shot below ~0.8x — it steps). Its own audio has no speech; dropped.
- Pixabay clips in `media/` (not in git; re-download with `editor/scripts/pixabay.py get <id> --out projects/short2/media`):
  31098 LED countdown ("10", and 4-3-2-1 callback), 93316 soda water pour ("CO2 paani se milkar"), 352974 neuron bolt
  ("sensors... acid check"), 99219 blue breath silhouette ("tez saansein"), 364928 AI underwater sun ("ya paani mein...
  practice kabhi nahi"), 366804 bubble column ("behoshi", with a 50% dim at the end), 129426 typing on a phone ("comment
  karo"). Tried and dropped: 908 freedivers (3.5x upscale, second diver reads as scuba), 61292 bald stock man, 34283
  holiday pool, 37712 plain bubbles, 123821 fashion underwater shoot.

## v2 edit
- 28 shots, ~1.7 s average (v1: 16 shots, only 12 visible cuts); every creator source range used once (the freeze on
  "Jawab, B!" holds the last frame of the shot before it). Cuts land on word starts (edl.json notes say which line).
- Hook: man inhales → snap to his face on "Abhi" → LED "10" on "10 second" → corner timer takes over and hits 0 on
  "band!", with a heartbeat on every timer second (no ticks). A/B cards + "JAWAB END MEIN 🔒"; CO2 molecules on
  "CO2 zyada"; freeze under "KAUN?"; freeze + flash + B ✅ / A ❌ on "Jawab, B!"; LED 4-3-2-1 callback on "Isiliye...";
  ending words pop as spoken ("TUMNE A SOCHA YA B? 🤔"), then COMMENT KARO on the typing shot.
- Fixes from the critique: brainstem ring lands on "brainstem!" (front view, then back view), sensors card on
  "sensors"; riser peaks on KAUN?; 'slam' hits (audible on phones); steady heartbeat (~60 bpm, one beat per timer
  second) under the hold, getting louder (breath-holding slows the heart — it must not speed up); whooshes on scene changes; captions max 16 chars
  (one line each); safety wording "Pehle tez saansein, phir rokna" / "Tez saansein ➡️ CO2 kam ➡️ alarm late"; "Oxygen
  ki kami NAHI" + "Badhta CO2" (carotid-body caveat goes in the pinned comment); blood "Acidic ki taraf, pH 7.4 se thoda
  neeche"; "CO2 banta rehta hai" (CO2 is masculine in the VO). Cards kept short enough to read (≤ ~4 words/s).
- QA findings fixed in the pipeline itself (build.py): camera resets snap to the cut frame (no one-frame zoom twitch
  at cuts) and a push-in can't run past the next cut.
- The creator's AI clips carry a small ✦ (Gemini/Veo) mark bottom-right; left as is.
- Music `documentary`, under_voice_db 15 (= CapCut volume 9 while talking), gap_db 10 (lifts a little on the logo).
- Title: "Saans Rokne Par Ghutan Kyon Hoti Hai? Asli Wajah CO2 Hai! #shorts". Pinned comment: A ya B question +
  "Tez saansein CO2 ghata deti hain, isliye ghutan ka alarm late bajta hai aur oxygen pehle khatam ho sakti hai
  (shallow water blackout). Paani mein breath-hold practice kabhi mat karo." + "oxygen ka bhi role hai (carotid
  body), par main trigger CO2". Sources: StatPearls (NBK554620), Parkes 2006 "Breath-holding and its breakpoint".
