# short4 — Venus par ek second (Hindi remake of the creator's English Venus Short)

## Where we are (2026-10-13)
- Creator sent `download/ref.mp4` (30.4 s English Short, AI footage: astronaut on Venus; Veo ✦ marks; burned-in English
  text "ONE SECOND / ON VENUS", "92× EARTH'S PRESSURE" (to ~7.1 s), "465°C" (to ~12.5 s)). Cuts at 7.4, 13.4, 18.5 (+ ~26.5).
- Asked for: a Hindi VO script only (they record the voice themselves), then the full edit "like the previous video" + 3D scenes.
- Script delivered: `script.md` (Devanagari to record + Roman captions + shot/3D plan + verified facts), `script.json`.
  Quiz structure like their Leh storyboard: lander quiz (A 2 min / B 2 ghante / C 2 din, answer B: Venera 13, 127 min).
- Waiting for: the creator's Hindi voice recording.

## Edit plan when the voice arrives
tighten_vo -> transcribe (hi) -> edl.json mixing ref.mp4 shots with Three.js 3D scenes (Venera lander + timer + quiz;
ocean depth + empty can crushing; Sun/Mercury/Venus thermometers; Venus globe in cloud shell with CO₂ greenhouse arrows) ->
cover the burned-in English text with our Hindi cards (same spot) -> captions (word_text: बानवे -> 92, चार सौ पैंसठ -> 465 on
the first word, blank the rest) -> "AI visual" tag on the AI footage -> pressure-cooker callback (whistle) -> documentary
music volume 9 -> channel end card with fades -> review -> deliver. 3D templates: `editor/templates/3d/` (earth_orbit, konark_wheel).
