# short3 — Leh mein dal kyun nahi galti: the CREATOR'S storyboard (verbatim, received 2026-10-12)

**This storyboard is the plan.** It replaces my earlier script in `vo/` (kept only as research/reference). The creator will provide
the actual voiceover and the real video footage later; until then only learn it, don't build.

Scene 1 — The hook
REAL
00:00–00:04 · 4 sec
Voiceover: “Leh mein dal ubal toh rahi hai… phir bhi jaldi galti kyun nahi?”

* Shot: Extreme close-up of bubbling dal.
* Camera: Slow push-in; steam visible.
* Sound: Natural bubbling plus a subtle impact.
* Text: `DAL JALDI KYUN NAHI GALT I?` Use the correct on-screen spelling: DAL JALDI KYUN NAHI GALTI?

Source: Film your own dal or use licensed stock footage. No AI needed.
Scene 2 — A/B/C quiz
REAL + TEXT
00:04–00:07 · 3 sec
Voiceover: “A: Oxygen kam? B: Thand? Ya C: Hawa ka pressure kam?”

* Shot: Real Leh mountain footage.
* Overlay: Three options appearing quickly.
* Sound: Three subtle ticks.

Source: Genuine Leh footage from a licensed stock library. Add all quiz text in CapCut.
Scene 3 — Altitude
REAL + GRAPHICS
00:07–00:13 · 6 sec
Voiceover: “Leh, samundar se lagbhag 3,500 metre upar hai. Wahan hawa ka pressure kaafi kam hota hai.”

* Shot: Mountain panorama.
* Graphic: Altitude counter rises to `3,500 m`.
* Graphic: Pressure gauge moves downward.

Source: Real footage is preferred; use AI for an atmospheric visualization only if necessary. Create the numerical overlays yourself.
Scene 4 — The 88°C reveal
AI + GRAPHICS
00:13–00:20 · 7 sec
Voiceover: “Isiliye khule bartan mein paani 100 nahi, lagbhag 88 degree Celsius par ubalne lagta hai.”

* Shot: Macro boiling-water visualization.
* Overlay: `100°C → ~88°C`.
* Camera: Slow macro push-in.

Source: AI video is useful for the close-up scientific visualization. Add the thermometer reading in CapCut; don't rely on AI to generate accurate text or numbers.
Scene 5 — Why more flame doesn't solve it
REAL
00:20–00:25 · 5 sec
Voiceover: “Aag tez karne se paani zyada tezi se ubalega, par uska temperature lagbhag 88 degree hi rahega.”

* Shot: Boiling water and gas flame.
* Overlay: `MORE HEAT ≠ MUCH HIGHER TEMP`.
* Keep the thermometer graphic steady.

Source: Real footage. Use a graphic to communicate the concept; don't pretend the footage was filmed at Leh.
Scene 6 — Answer reveal
GRAPHICS
00:25–00:29 · 4 sec
Voiceover: “Sahi jawab hai C: kam atmospheric pressure!”

* Shot: Simple diagram showing the relationship between external pressure and boiling point.
* Overlay: `C — LOW AIR PRESSURE`.
* Sound: Short reveal hit.

Source: Build this in CapCut. AI footage is unnecessary because a clean diagram explains the science more accurately.
Scene 7 — The solution
REAL
00:29–00:36 · 7 sec
Voiceover: “Pressure cooker andar ka pressure badhata hai, jisse paani aur garam ho sakta hai aur dal jaldi galti hai.”

* Shot: Pressure cooker on the stove, followed by cooked dal.
* Overlay: `PRESSURE ↑` and `COOKING TEMP ↑`.
* Transition: Cut from the cooker to soft dal.

Source: Real footage is best. If you use an AI cutaway, label it as a conceptual illustration and avoid fake precision. Never open a pressurized cooker for a shot.
Scene 8 — CTA
REAL
00:36–00:40 · 4 sec
Voiceover: “Tumhara jawab A, B ya C tha? Comment karo!”

* Shot: Finished dal.
* Overlay: `A, B YA C? COMMENT KARO!`
* Branding: Small Science Unseen Hindi logo.

Source: Real food footage. Keep the ending clean and readable.

---

## My notes (learning only; nothing built from this yet)
- 8 scenes, 40 s total (4+3+6+7+5+4+7+4). Scene labels: REAL / AI / GRAPHICS tell which picture comes from the creator's footage, which
  from AI/generated visuals, and which from overlays we draw. Numbers and text are always drawn by us (never by AI).
- The creator's wording already fixes the points my research flagged: "jaldi galti kyun nahi" (not "nahi galti"), "khule bartan mein"
  (open pot), "hawa ka pressure kam" (not just "pressure kam"), "lagbhag 88 degree", cooker raises pressure and temperature.
- Do not claim the footage was filmed in Leh unless it was (scene 5). Never show a pressurized cooker being opened (scene 7).
- When the voice + footage arrive: use the "new voiceover over existing footage" workflow in CLAUDE.md (tighten VO, transcribe, one EDL
  shot per scene, `assemble.py`, plan, build, review). Captions in the Konark style, music `documentary` volume 9, logo end card with
  fades (small logo in scene 8), thumbnail + title/tags/captions later. Sound: bubbling + subtle impact (1), three ticks (2),
  reveal hit (6).
- Overlays to prepare once footage exists (some need new templates): A/B/C option cards appearing quickly (2); altitude counter to
  "3,500 m" + pressure gauge needle falling (3); thermometer "100°C → ~88°C" (4) kept steady on the flame shot (5) with
  "MORE HEAT ≠ MUCH HIGHER TEMP"; pressure-vs-boiling-point diagram + "C — LOW AIR PRESSURE" (6); "PRESSURE ↑ / COOKING TEMP ↑"
  (7); "A, B YA C? COMMENT KARO!" + small logo (8). Verified numbers for these are in `NOTES.md` (Leh 88.2 C, ~65 % pressure, cooker ~114 C).
- Open: the AI macro boiling shot (scene 4) — creator's call whether to generate/ask for it or have me draw a graphic. Stock sites are
  blocked here, so the creator supplies all real footage (including Leh mountain clips).
