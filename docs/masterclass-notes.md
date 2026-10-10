# What I learned: "Master AI Video Editing in 20 Minutes | Claude AI Editing Masterclass"

Source: https://youtu.be/hffQ4UleKUU — *Last Moment Tuitions* (Sumer Singh Rajpurohit), Hindi, 22:01, published 2026-10-01.
I studied it two ways: the full Hindi transcript, and a frame-by-frame visual walkthrough (what is on screen, which prompts are typed, how each edit looks).

---

## The big idea

You don't open an editor. You give Claude:

1. **the raw clip** (drag-drop, or better: its file **path**, so you don't upload it again every time),
2. **a plain-English goal** (captions, b-roll, music, motion graphics, SFX, a style to copy),
3. **one or two hard rules** (the most important one: *never cover my face*),

and then you **review and iterate** ("captions are on my face, fix this", "v1 → v7").

The tools doing the work underneath (visible in his terminal): **Whisper** (transcribe), **ffmpeg** (cut/encode/audio),
**HyperFrames** by HeyGen (HTML → video motion graphics, rendered by headless Chrome), **Blender** (3D), plus web search for b-roll/music.

---

## The 6 steps, one by one

### Step 1 — One-prompt explainer edit (01:14–04:09)
Raw clip: a talking-head about software-engineer CTC salary.

> I want to edit this video. This is an explainer video. Add some motion graphics, proper text, required sound effects.
> Also before edit go through the video, understand it and tell me what can be made better.

Then he only typed **"do it"**.

What Claude did: transcribed, split audio into chunks, pulled keyframes, **suggested improvements first**, fixed repetitions,
made it **9:16 (1080×1920)**, added **Hinglish word captions with yellow/white keyword highlights**, **zoom punches**,
**data cards / boxes** that explain numbers (CTC → base pay 9.6L of 12L), a **bar chart**, and subtle **SFX** on each pop.

Lesson: *ask for a review before the edit* — the AI acts like a senior editor, not just a button.

### Step 2 — Setup HyperFrames, web b-roll, copyright-free music (04:10–06:42)
1. Google "HyperFrames" → copy the GitHub link (`heygen-com/hyperframes`) → paste into Claude:
   `setup hyperframes so we can use to edit videos`
2. Give the clip **path** instead of uploading:

> Path: /Users/.../C3266.MP4
> Edit this. Put proper caption, put B-rolls — use the free version from internet, non-copyright, licence-free —
> put background music from YouTube library, non-copyright.

Result: face-centered 9:16 crop, stock b-roll matching the words (stress, filming on phone), captions placed **below the chin**,
music at a low, normalized level. (Claude asked him to sign in to YouTube Audio Library once.)

### Step 2.1 — Your OWN b-roll library (06:43–09:34)
He had years of unorganized phone clips. Prompt (in his words): *"This folder has my videos. This is my photo — this is how I look.
Watch all the videos, rename/categorize where I appear (walking, dancing, travel, family…), and make me a list so next time you can use my own b-roll."*
Claude produced folders (`01 Talking to Camera`, `02 Walking`, `03 Dancing`, `07 Snow`, `13 Family and Home`…) and a **`Clip List.csv`**.

Then the fix-and-reuse prompt:

> In this video captions are coming on the face — solve this.
> Also this time use my own B-rolls from the path given below; use the clip list file to select relevant b-rolls.
> Path: /Users/.../Broll/

Lesson: **index once, reuse forever**. Review → name the problem precisely → fix.

### Step 3 — Copy a top creator's editing style (09:35–13:22)
Reference: an **Ankur Warikoo** Short (Mumbai 1BHK prices). Same recipe works for GeeksforGeeks / Apna College puzzle Shorts (20M+ views).

> Take this Ankur Warikoo YouTube Short and decode its editing style — motion graphics, cuts, pacing, captions, transitions, music and sound effects.
> Now use what you learned to edit my raw video in the same style with the same energy.
> Keep my content original, but make the editing, motion and sound equally engaging and professional.
> Raw clip path: …

Result: split layout (graphic box on top, him below), Mumbai map, **rising bar chart** of price ranges per area
(Vasai-Virar 35–50L … South Mumbai 2–4 Cr), SFX on each text pop. For the puzzle Short: a **countdown before the answer**
and a "comment your answer" CTA.

Lesson: **the better the reference you give, the better the edit you get.**

### Step 4 — Apple-style clean motion graphics, face always visible (13:23–15:46)
Long prompt (he wrote it in Notion), the key parts:

> Edit this to be super engaging and clean with HyperFrames. Apple-style, super clean motion graphics and animation.
> First transcribe my video so you know exactly when each animation, text, image or effect should appear as I speak.
> Add relevant B-roll, screenshots, screen recordings, images or generated visuals with smooth animations from the left and right.
> …make sure it doesn't cover my face, which is in the middle of the screen.
> **Keep my face clearly visible at all times. After editing, review the frames and make sure no graphic, B-roll or animation covers my face or important content.**

He says that last line works in **every** prompt. First result wasn't great; he iterated to **v7** ("har patthar se aam nahi girta").

### Step 5 — Channel intro from a reference (15:47–17:40)
Reference: an Opus-made intro posted on X. Prompt:

> 1. Analyze the attached video. What makes its design, pacing, frame types and energy so good?
> 2. Turn that into a reusable motion-design skill.
> 3. Use the skill to make a 15-second YouTube video in 16:9 (1920×1080). Research YouTube, collect b-roll and assets,
>    make it unmistakably YouTube-branded: colors, typography and design language. Feature my channel.

Result: beat-synced (~128 BPM) 15s intro, HUD overlays, subscriber counter, play button, channel name.
Lesson: **turn a good result into a reusable "skill"** so every next video is consistent.

### Step 6 — 3D animation like Nitish Rajput (17:41–22:01)
Reference: "How astronauts sleep in space". Prompt:

> Watch this Nitish Rajput YouTube Short. Break down its editing style: 3D animation, motion graphics, cuts, pacing, captions,
> transitions, music and sound effects. If you can't open the link, tell me before continuing.
> Then edit my raw video in the same style and with the same energy, and build all the 3D animations yourself.
> Render everything on this machine. Install any tools you need, such as Blender and ffmpeg.
> Keep my content original, but make the editing, motion and sound just as engaging and professional.

Needed a GPU PC; first run took ~2–2.5 h (setup), later ones ~45–60 min. 2–3 prompts to get it right.
Result: rotating Earth, ISS orbit with 16 sunrises/day, pressurized cabin, floating sleeping bag on the wall.

---

## How he teaches (and why it works)
- **Show the result first, then the method.** The video opens with the finished edit and intro, *then* says "I made this with Claude".
- **Before → after** for every step: raw clip, then prompt, then output.
- **Beginner-first language**: "no terminal, no technical stuff", explains jargon on the spot ("motion graphic = these boxes/designs").
- **Ladder of difficulty**: one prompt → web assets → own assets → copy a pro style → Apple-style → intro → 3D.
- **Honesty about iteration**: v1 wasn't good, v7 was. Each fix prompt names *one* concrete problem.
- **Money framing**: editors charge ₹2,000–10,000 per video; this skill is worth money.
- **Retention tricks in his own video**: hook question in the first 3 s, "watch till the end", mid-video like/hype ask,
  "answer in the next second… comment first", a challenge at the end (post your edit, tag me, best one gets a shout-out).

## The editing rules I'm taking from it (my checklist for your Shorts)
1. Hook in the first 1–3 s (question / bold number / payoff preview). Cut every dead pause and repeat.
2. 9:16, 1080×1920, face-centered. **Never** put text, b-roll or graphics on the face — check frames after rendering.
3. Word-by-word captions, 2–4 words per line, bold font, **keyword highlight colour**, sitting below the chin (not in the bottom 15% UI zone).
4. Every number/claim becomes a **visual** (card, counter, bar chart, map, icon). Graphics slide in from left/right, Apple-clean.
5. **Punch-in zooms** on emphasis words; change the frame every 2–4 s so the eye never rests.
6. SFX on every visual event (whoosh on slide, pop on text, ding on reveal, riser before payoff) — subtle, not loud.
7. Music bed only under the voice: ducked low (voice ≈ −14 LUFS overall; music ~18–22 dB under the voice).
8. Copyright-free assets only (own b-roll, generated visuals, licence-free music/SFX).
9. Style transfer: decode a reference Short (cuts/min, caption style, colours, SFX) and match its energy, keep your content.
10. End with a CTA / loop back to the hook. Then **review, name one problem, fix, repeat**.
