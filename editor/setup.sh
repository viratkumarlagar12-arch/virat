#!/usr/bin/env bash
# One-time setup for the Shorts editor (the masterclass's "setup hyperframes" step, plus everything
# else the pipeline needs). Safe to re-run; skips what is already there.
#   bash editor/setup.sh            # core
#   WITH_BLENDER=1 bash editor/setup.sh   # + Blender (bpy) for photoreal 3D
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ED="$ROOT/editor"
MODELS="$ED/models"
REL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
TTS_REL="https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"
ZOO="https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models"
CTC="sherpa-onnx-omnilingual-asr-1600-languages-300M-ctc-v2-int8-2026-02-05"
fetch() { curl -fL --retry 4 --retry-delay 2 "$@"; }

echo "==> Python venv (speech-to-text, face tracking, audio)"
[ -x "$ROOT/.venv/bin/python" ] || python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install -q --upgrade pip
"$ROOT/.venv/bin/pip" install -q -r "$ED/requirements.txt"
if [ "${WITH_BLENDER:-0}" = "1" ]; then "$ROOT/.venv/bin/pip" install -q bpy; fi

echo "==> HyperFrames CLI, GSAP, Three.js, fonts (npm) + pinned Chrome for rendering"
(cd "$ED" && npm install --silent && HYPERFRAMES_NO_TELEMETRY=1 npx hyperframes browser ensure >/dev/null)

echo "==> Models"
mkdir -p "$MODELS"
[ -d "$MODELS/sherpa-onnx-whisper-turbo" ] || fetch "$REL/sherpa-onnx-whisper-turbo.tar.bz2" | tar -xj -C "$MODELS"
[ -d "$MODELS/$CTC" ] || fetch "$REL/$CTC.tar.bz2" | tar -xj -C "$MODELS"
[ -f "$MODELS/silero_vad.onnx" ] || fetch -o "$MODELS/silero_vad.onnx" "$REL/silero_vad.onnx"
[ -f "$MODELS/face_detection_yunet_2023mar.onnx" ] || fetch -o "$MODELS/face_detection_yunet_2023mar.onnx" \
  "$ZOO/face_detection_yunet/face_detection_yunet_2023mar.onnx"
[ -f "$MODELS/face_recognition_sface_2021dec.onnx" ] || fetch -o "$MODELS/face_recognition_sface_2021dec.onnx" \
  "$ZOO/face_recognition_sface/face_recognition_sface_2021dec.onnx"
# text-to-speech voices for tts.py: 3 Hindi Piper voices + Kokoro v1.0 (hf_alpha/hf_beta/hm_omega/hm_psi).
# Not Kokoro v1.1 (Chinese/English voices only) and not the int8 v1.0 build (steady 4.8/9.6 kHz whine, 3x slower).
mkdir -p "$MODELS/tts"
for m in vits-piper-hi_IN-rohan-medium vits-piper-hi_IN-pratham-medium vits-piper-hi_IN-priyamvada-medium \
         kokoro-multi-lang-v1_0; do
  [ -d "$MODELS/tts/$m" ] || fetch "$TTS_REL/$m.tar.bz2" | tar -xj -C "$MODELS/tts"
done

echo "==> Fonts (Latin + Devanagari TTFs), sound-effect library"
"$ROOT/.venv/bin/python" "$ED/scripts/fonts.py" "$ED/node_modules/@fontsource" "$ED/assets/fonts"
[ -f "$ED/assets/sfx/whoosh.wav" ] || "$ROOT/.venv/bin/python" "$ED/scripts/sfx.py" "$ED/assets/sfx"

echo "==> Ready. See README.md for the editing workflow."
