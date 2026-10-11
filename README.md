# Virat — AI Shorts editor (Claude + HyperFrames)

Everything from the masterclass **"Master AI Video Editing in 20 Minutes | Claude AI Editing Masterclass"**
(https://youtu.be/hffQ4UleKUU), rebuilt as a working pipeline in this repo. You send a raw Short; Claude edits it
to a professional level: jump cuts, 9:16 face-centred framing, word-by-word captions, motion graphics, b-roll,
zoom punches, sound effects, music, loudness — and checks every frame so nothing covers your face.

- What I learned from the video, step by step: [`docs/masterclass-notes.md`](docs/masterclass-notes.md)
- Every edit option: [`docs/plan-reference.md`](docs/plan-reference.md)

## How we work (you ↔ Claude)
1. **You** upload your raw Short (or give its path).
2. **Claude** watches it (frame sheets + transcript), tells you what can be better (masterclass step 1),
   then writes the edit plan and renders **v1**.
3. **You** review and name one problem at a time ("caption on my face", "music too loud", "use my b-roll").
4. **Claude** fixes and renders **v2, v3 …** until it's right.

Optional extras: your own b-roll folder (step 2.1), a reference Short whose style you want copied (step 3),
your channel name for an intro (step 5), a topic that needs 3D (step 6).

## Sending your video (the chat has a 30 MB limit per file)
The Claude app refuses attachments over 30 MB ("some images were too large to attach"). Google Drive, Dropbox,
WeTransfer and Telegram links don't work from this cloud machine; GitHub does. Pick one:

1. **Make it smaller than 30 MB, then attach** (easiest). In CapCut: import the video → Export → Resolution
   **1080p**, Frame rate **30**, Code rate **Recommended** or **Lower**, and check the file size it shows before exporting.
   Rule of thumb: about 27 MB for a 60-second Short at 1080p — YouTube compresses Shorts to about this level anyway.
   On a computer: `ffmpeg -i in.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2" -c:v libx264 -preset slow -crf 23 -maxrate 3.5M -bufsize 7M -c:a aac -b:a 160k out.mp4`
2. **Split it** into 2–3 parts, each under 30 MB, and attach all of them in one message. Claude joins them back.
3. **Full original quality, any size (up to 2 GB): a GitHub release.** On github.com/viratkumarlagar12-arch/virat
   (phone browser works) → **Releases** → **Draft a new release** → tag e.g. `raw-1` → drag the video into
   "Attach binaries" → **Publish**. Tell Claude the tag. ⚠️ The repo is public, so anyone with the link can download
   the video while the release exists. Delete the release once Claude confirms it has the file.

## The 6 masterclass steps → tools here

| Step in the video | Here |
|---|---|
| 1. One-prompt explainer edit (motion graphics, text, SFX, "tell me what can be better") | `analyze.py` + `transcribe.py` → plan → `build.py` |
| 2. Setup HyperFrames, b-roll, copyright-free music | HyperFrames CLI installed by `setup.sh`; b-roll overlays; `music.py` composes licence-free beds (or use your own track) |
| 2.1 Index your own b-roll (who/where/what), clip list | `broll_index.py scan <folder> --me photo.jpg` → `organize` |
| 3. Copy a top creator's style (Warikoo, Apna College…) | style-decode checklist in `docs/plan-reference.md` → themes, caption styles, graphic types |
| 4. Apple-style clean motion graphics, face always visible, review frames | `theme: clean`, face-safe zones, `review.py` face check |
| 5. Channel intro from a reference / reusable motion skill | a HyperFrames composition made for your channel (needs your channel name/logo), rendered with `render3d.py` (renders any standalone template) |
| 6. 3D animation like Nitish Rajput (Blender) | `templates/3d/earth_orbit.html` (Three.js, fast) + Blender `bpy` for photoreal shots |

## Commands
```bash
bash editor/setup.sh                                   # once per machine (models, fonts, renderer)
P=projects/my_short
.venv/bin/python editor/scripts/analyze.py raw.mp4 $P/work      # probe, face track, pauses, frame sheets
.venv/bin/python editor/scripts/transcribe.py $P/work           # word-level Hindi/English transcript
#   -> write $P/plan.json
.venv/bin/python editor/scripts/build.py $P                     # render out/<name>_vN.mp4
.venv/bin/python editor/scripts/review.py $P                    # frame sheets, face check, loudness
```

## What's inside
- **Speech-to-text**: Whisper large-v3-turbo (text, great with Hinglish) + Meta Omnilingual CTC (exact word timing).
- **Faces**: OpenCV YuNet (where the face is → safe zones, reframing) + SFace (is this clip me?).
- **Motion graphics**: HyperFrames (HTML → video, headless Chrome) + GSAP; 3D with Three.js; fonts Poppins,
  Montserrat, Inter, Anton, Mukta/Noto Devanagari.
- **Audio**: voice clean-up (high-pass, denoise, EQ, compression), synthesized SFX and music (no copyright),
  music ducking under speech, mastered to −14 LUFS / −1.5 dBTP (YouTube standard).
- **Output**: 1080×1920, 30 fps, H.264 + AAC 320 kbps.

Note: YouTube Audio Library is not reachable from this cloud machine, so music and SFX are generated here
(copyright-free). B-roll comes from your own clips, generated graphics/3D, files you upload, or Pixabay
(`editor/scripts/pixabay.py`, free licence; needs the `PIXABAY_API_KEY` environment variable).
