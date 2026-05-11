# InClave demo recording.
#
#   vhs demo.tape          → writes demo.gif at the repo root
#
# Requires: charm.sh's vhs (`brew install vhs`), and:
#   - ollama running on 127.0.0.1:11434 with `qwen2.5-coder:7b` pulled
#     (coding-tuned model — much more reliable than llama3.2:3b for the
#     auto-run flow; needs ~5 GB unified memory)
#   - `inclave` on PATH (uv tool install --force --from packages/cli inclave-cli)
#   - demo data copied into $HOME/.inclave-demo/ (mrr_2026.csv +
#     q1_review.pdf — both checked into demo-data/ in this repo).

# Path is relative to wherever vhs is invoked. From repo root, run as
# `vhs demo-data/demo.tape` and the gif lands at demo-data/demo.gif.
Output demo-data/demo.gif

# Pure-black background, minimal colors. "Terminal on a dark page".
Set Theme { "name": "InClave", "background": "#000000", "foreground": "#e6e6e6", "cursor": "#e6e6e6", "selection": "#3a3a3a", "black": "#000000", "red": "#ff6b6b", "green": "#6ad673", "yellow": "#f0c674", "blue": "#7fb3ff", "magenta": "#c792ea", "cyan": "#7ce0e0", "white": "#e6e6e6", "brightBlack": "#5c5c5c", "brightRed": "#ff8787", "brightGreen": "#8ce28d", "brightYellow": "#ffd47e", "brightBlue": "#9ec4ff", "brightMagenta": "#dcb6ff", "brightCyan": "#a4ecec", "brightWhite": "#ffffff" }

Set FontSize 16
Set Width 1200
Set Height 760
Set Padding 22
Set TypingSpeed 30ms
Set Framerate 30
# Playback at 1.5x so the gif feels snappy. The model still takes its
# real time to think — this just speeds the rendered output.
Set PlaybackSpeed 1.5

# --- setup (off-camera) ----------------------------------------------------
Hide
Type "cd ~/.inclave-demo && inclave models use qwen2.5-coder:7b && clear" Enter
Sleep 2s
Show

# --- the recorded demo -----------------------------------------------------
Sleep 400ms
Type "inclave"
Sleep 200ms
Enter
Sleep 2s

# Turn 1: ask a quantitative question over a CSV. Model writes Python,
# inclave runs it in the sandbox automatically, model summarizes.
# Phrasing is explicit ("print … using mrr_usd column") to keep the
# generated code on the happy path.
Type "~/.inclave-demo/mrr_2026.csv  print total mrr_usd growth in % from the first to the last row"
Sleep 200ms
Enter
# Turn 1 (qwen2.5-coder:7b on M1 Pro):
#   stream code      ~12s
#   sandbox          ~1s
#   stream summary   ~8s
# = ~21-25s practical minimum; 28s leaves headroom.
Sleep 28s

# Turn 2: drop a PDF and ask for plain-text extraction. Phrasing tells
# the model "from this PDF" so it doesn't fall back to the CSV.
Type "~/.inclave-demo/q1_review.pdf  from this PDF, list the top 3 things that blocked Q1"
Sleep 200ms
Enter
# Text-only turn — no sandbox. qwen's PDF answers are longer than llama's.
Sleep 14s

Type "/exit"
Enter
Sleep 300ms
