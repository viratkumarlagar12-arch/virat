# Notes for Claude: this repo is a Shorts editing pipeline

The user (Virat) sends raw YouTube Shorts and wants them edited to a professional level, following the
masterclass summarised in `docs/masterclass-notes.md`. Talk to them in simple English (they write Hinglish).

## Fresh container? Run setup first
`bash editor/setup.sh` (≈2 GB of models/renderer; idempotent). Network here: GitHub releases, media.githubusercontent,
npm and PyPI work; Hugging Face, stock-footage sites, YouTube and most CDNs are blocked — that's why models come
from sherpa-onnx GitHub releases and music/SFX are synthesized.

## Getting the raw video
Chat attachments are capped at 30 MB (the app says "some images were too large to attach"). Drive/Dropbox/WeTransfer
are blocked here. Large originals come as a GitHub release asset on the user's public repo: find the asset name with
the GitHub MCP release tools (`get_release_by_tag`), then
`curl -fL -o projects/<name>/raw.mp4 https://github.com/viratkumarlagar12-arch/virat/releases/download/<tag>/<file>`.
Then remind the user to delete the release (the repo is public). Split uploads: join with ffmpeg concat
(`-f concat -safe 0 -i list.txt -c copy`, or re-encode if the parts' codecs differ).

## Workflow for every video
1. Put the raw file in `projects/<name>/` (never commit media; `.gitignore` covers it).
2. Already-edited CapCut exports often have black bars (a clip/photo not filling 9:16): run
   `fill_bars.py raw.mp4 projects/<name>/fixed.mp4 [--keep-from <end-card start>]` and edit `fixed.mp4`.
   Then `analyze.py <video> projects/<name>/work` and `transcribe.py projects/<name>/work [--lang hi|en]`.
   For Hindi, transcribe uses the Omnilingual CTC words (sherpa's Whisper drops Devanagari bytes); some CTC words
   come out in the wrong script (Bengali/Tamil letters) — the Whisper line and context tell you the real word.
   Faceless videos: `"layout": {"face": "none"}` (face detection finds "faces" in carvings/patterns).
3. LOOK at `work/sheets/*.jpg` (Read the images) and read `work/transcript.txt`. Fix transcript mistakes via
   `word_text` in the plan. For Hinglish captions, transliterate Devanagari words to Roman via `word_text`.
4. First reply = what can be better (hook, dead air, retakes, missing visuals) — masterclass step 1 — then edit.
5. Write `projects/<name>/plan.json` (`docs/plan-reference.md`). Every number/claim → a visual; hook in first 2 s;
   punch-ins on emphasis; SFX on visual events; CTA at the end. Keep graphics off the face (zones are automatic).
6. `build.py projects/<name>` (add `--no-render` to iterate on layout; `--remix` for audio-only changes reuses the
   last picture render and takes minutes instead of ~20; `hyperframes check` runs in `projects/<name>/hf`).
   Build prints "note: … shortened" when two graphics collide — re-time them in the plan.
7. `review.py projects/<name>` → look at `work/review/final_*.jpg`, face check must say OK, loudness ≈ −14 LUFS.
8. Deliver with SendUserFile (30 MiB cap: build.py also writes `<name>_vN_upload.mp4` when needed); ask for one
   round of notes; bump version (v2, v3…).

## New voiceover over existing footage (example: `projects/konark_v3`)
`tighten_vo.py` shortens the pauses in the VO → transcribe it → write `edl.json` (one shot per line of the script) →
`assemble.py edl.json assembled.mp4` (it warns when a shot runs across a source cut; check those frames) →
`analyze.py assembled.mp4 work` → plan with `"cuts": {"auto": false}` → build. Shots after the voice ends get silence.

## AI voiceover ("you give new voice over")
`tts.py <voice> script.txt out.wav --speed 1.34 --pauses '[...]' --json timings.json` — free offline Hindi voices
(Kokoro v1.0 `hm_omega`/`hm_psi` male, `hf_alpha` female; Piper `rohan`/`pratham`/`priyamvada` are flatter). Write the
script in Devanagari with English words transliterated (CO2 → सीओटू), keep a Roman copy for captions, and check the
result with an ASR round trip (Omnilingual CTC). vidIQ's voiceover tool (ElevenLabs) sounds more natural but spends
the user's vidIQ credits — ask first. Example: `projects/short2/vo/`.

## Channel end card
The user's channel is "Science Unseen Hindi". Their CapCut exports end with a ~1.5 s still logo card (black,
"SCIENCE / UNSEEN HINDI" over the Earth; in the Konark upload it starts at 44.467 s, 480×854). When they ask for
"my channel clip at the end", append it as the last shot (~2 s; in-point a frame after its start), dip to black and
fade the logo in, slow push-in (it's a still), fade out to black at the end (`fade` overlays — the user asked for
fades over a flash), stop captions before it (`captions.until`), and let the music fade out under it.

## Music level
The user thinks in CapCut terms: "music 8 to 10 volume" → `"music": {"volume": 9}`. Phone speakers don't play
sub-bass, so a bass-heavy bed is inaudible on a phone even when the meter says it's there — use the `documentary`
mood (or another with mid-range content) for facts/history videos.

## Gotchas
- HyperFrames lint: no CSS transform on elements GSAP animates; video b-roll must be in index.html statically
  (build.py writes it); timeline registers after fonts load (inline script in index.html).
- Render speed ≈ 4.5× real time at 1080×1920 on 4 CPUs; Blender Cycles ≈ 20 s/frame at full res — prefer
  Three.js templates (`editor/templates/3d/`) unless photoreal 3D is needed.
- Test project: `projects/_test/plan.json` (regenerate its clip with `editor/scripts/make_test_clip.py`).
