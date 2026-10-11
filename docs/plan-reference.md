# `plan.json` reference

The plan is the whole edit, written after watching the contact sheets and reading `work/transcript.txt`.
Times are **source seconds** (as in the transcript) unless noted. Anything can be anchored to a word with
`"w": <word index>` (+ optional `"dt"` offset in seconds) — word indices are in `work/transcript.json`.
Use `"t_out"` for an exact time in the finished video.

```jsonc
{
  "name": "salary_short",            // output file name -> out/salary_short_vN.mp4
  "theme": "bold",                   // bold (dark cards, Montserrat, yellow) | clean (Apple, white cards, Inter) | desi (Poppins, white cards, red)
  "theme_vars": {"--accent": "#FFD60A"},   // optional colour overrides
  "grade": "punchy",                 // none | natural | punchy | warm | cinematic | upscale (480p/720p sources)
  "layout": {"face": "none"},        // faceless (b-roll + voiceover): graphics above centre, zooms from centre.
                                     // or "face": [x0,y0,x1,y1] in output px to override the detected face
  "reframe": {"zoom": 1.0},          // >1 crops tighter (4K sources)

  "cuts": {
    "auto": true,                    // keep only speech, remove dead air
    "max_pause": 0.22,               // pauses longer than this get cut
    "pre": 0.08, "post": 0.14,       // breathing room around words
    "remove_words": [12, 13, 14],    // retakes / fillers / repeated lines (by word index)
    "remove": [[31.2, 33.0]],        // any source range
    "trim": [0.5, 58.0]              // hard in/out
  },

  "word_text": {"5": "CTC", "9": "₹12 lakh"},   // fix or transliterate caption text per word (Hinglish etc.)

  "captions": {
    "style": "pop",                  // pop (word-by-word) | karaoke (pill behind active word) | clean
    "size": 84, "max_words": 3, "max_chars": 18,
    "uppercase": true,
    "keywords": ["salary", "CTC"],   // always highlighted (numbers/₹/% are auto-highlighted)
    "highlight": [22, 40],           // word indices to highlight
    "hide_words": [3],               // don't caption these (e.g. "umm")
    "breaks": [17],                  // force a new caption line at this word
    "emoji": {"40": "🔥"},           // emoji pops after a word
    "y": null,                       // auto (below the chin) — or a fixed pixel centre
    "until": 40.13,                  // optional (src sec): no captions from here on, e.g. a channel end card
    "off": false
  },

  "camera": {
    "cut_zoom": 1.08,                // alternate 1.0 / 1.08 at every jump cut (hides the jump)
    "drift": true,                   // slow push-in on long takes
    "punches": [{"w": 22, "scale": 1.12, "hold": 1.0}],   // emphasis punch-in
    "shakes": [{"w": 40, "amp": 14, "dur": 0.35}],
    "punch_sfx": "swoosh"            // optional sound on every punch
  },

  "overlays": [
    {"type": "hook", "t_out": 0, "dur": 2.6, "text": "₹1.5 *CRORE* salary?", "boxed": true, "sub": "sach ya jhooth? 👀"},
    {"type": "card", "w": 13, "dur": 2.2, "icon": "💰", "label": "CTC", "value": "*₹12* LPA", "sub": "cost to company", "side": "left"},
    {"type": "stat", "w": 18, "dur": 2.4, "from": 0, "to": 9.6, "decimals": 1, "prefix": "₹", "suffix": "L", "label": "Base pay", "end_sfx": "cash"},
    {"type": "bars", "w": 35, "dur": 3.6, "title": "Mumbai *1BHK*", "items": [{"label": "Thane", "value": 77, "display": "₹65–90L", "w": 37}]},
    {"type": "list", "w": 61, "dur": 3.2, "title": "Checklist", "items": [{"text": "Hook in *3s*", "w": 62}, {"text": "No dead air", "bad": true}]},
    {"type": "compare", "w": 66, "dur": 2.4, "a": {"title": "CTC", "value": "₹12L", "win": true}, "b": {"title": "In-hand", "value": "₹8.4L", "lose": true, "w": 68}},
    //   compare sides can also be "dim": true (greyed out, not marked wrong); "value_size": 62 for longer values
    {"type": "emoji", "w": 22, "dur": 1.6, "emoji": "🤯", "side": "right"},
    {"type": "image", "w": 47, "dur": 2.3, "src": "media/photo.jpg", "caption": "optional", "side": "right"},   // pip card
    {"type": "video", "w": 53, "dur": 2.0, "src": "/path/broll.mp4", "mode": "full", "media_start": 3.0},     // full-screen cutaway
    {"type": "lower_third", "w": 3, "dur": 2.5, "name": "Virat", "role": "Creator"},
    {"type": "countdown", "w": 70, "n": 3, "tag": "Comment your answer!"},
    {"type": "timer", "w": 5, "until_w": 31, "n": 10, "times": {"start": {"w": 7}}, "x": 905, "y": 335, "size": 210,   // small corner
     "tick_db": -12, "zero_sfx": "none", "tag": "Ab saans lo"},     // countdown pinned at x/y; counts from t_start, red at 0
    {"type": "chain", "w": 57, "until": 26.3, "title": "*SIGNAL*",  // cause -> effect: nodes light up one by one, arrows between
     "items": [{"icon": "📡", "text": "Sensors", "w": 58}, {"icon": "🧠", "text": "Breathing centre", "w": 59}]},
    {"type": "text_slam", "w": 76, "dur": 1.2, "text": "*FINALLY*"},
    {"type": "flash", "w": 76},                      // "in": 0 = full white on the first frame (flash on a hard cut)
    {"type": "fade", "t_out": 39.8, "in": 0.3, "hold": 0, "out": 0.5},  // dip to black over everything (also "color")
    {"type": "fade", "t_out": 41.6, "in": 0.5, "out": 0},               // ...or finish the video on black
    {"type": "sundial", "w": 45, "until_w": 71, "title": "Sooraj + Shadow = *Time*",   // wheel-as-sundial explainer
     "times": {"shadow": {"w": 55}, "move0": {"w": 59}, "move1": {"w": 71}}},          // named moments -> t_shadow, ...
    {"type": "cta", "w": 78, "dur": 2.4, "text": "Follow for *Part 2*", "button": "SUBSCRIBE"},
    //   or "button": "COMMENT KARO", "icon": "💬", "done": false  (button only bounces, no SUBSCRIBED state)
    {"type": "list", "w": 91, "until": 41.95, "variant": "calm", "title": "⚠️ DHYAN RAHE", "items": [...]}
    //   "variant": "calm" on card/list = yellow card with dark text (safety notes that shouldn't look alarming)
  ],
  // every overlay: "zone": "auto" | "top" | "lower" | "body" | "center" | [y0, y1]  (auto keeps it off the face)
  //                "sfx": "<name>" | "none"      (each type has a sensible default)
  //                "until_w": <word> | "until": <src sec> instead of "dur"
  // *word* in any text = accent colour

  "sfx": [{"w": 30, "name": "ding", "gain_db": -2}],
  // library: whoosh swoosh whoosh_down pop bubble click tick ding cash success riser impact glitch typing camera

  "music": {"mood": "upbeat", "seed": 3, "under_voice_db": 19, "gap_db": 11},
  // moods: upbeat lofi cinematic tech suspense documentary (piano + strings; the one that's heard on phone speakers)
  // or "volume": 9 instead of the dB pair = CapCut-style music volume (100 = full track; 10 ≈ 14 dB under the voice)
  // mood: upbeat | lofi | cinematic | tech | suspense  — or {"file": "my_track.mp3"} for your own licence-free track

  "progress_bar": true
}
```

## Zones (all automatic)
`analyze.py` finds where the face moves; `build.py` turns that into pixel zones that never touch it:
**top** (above the head), **lower** (between chin and captions), **body** (chin to the bottom safe line —
captions drop lower while a body graphic is on), **center/full** (deliberate cutaways). Text also stays out
of the Shorts UI (top 150 px, bottom 340 px). Two graphics never share a zone at once — the earlier one
exits as the next arrives (build prints a note when it shortens one).

## Style decode checklist (step 3: copy a creator's editing style)
When given a reference Short, write down — then express it with the plan fields above:
cuts per minute · zoom pattern (cut alternation / punches) · caption font, size, case, colours, words per line,
position · graphic types and when they appear (numbers → stat/bars, lists → list, A vs B → compare) ·
entry motion (slide side / pop / slam) · SFX on which events · music mood + level · hook format (first 2 s) ·
CTA/loop at the end · colour grade.
