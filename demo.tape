# InClave demo recording.
#
#   vhs demo.tape          → writes demo.gif at the repo root
#
# Requires: charm.sh's vhs (`brew install vhs`), and:
#   - ollama running on 127.0.0.1:11434 with `llama3.2` pulled
#   - `inclave` on PATH (uv tool install --force --from packages/cli inclave-cli)
#   - demo data in $HOME/.inclave-demo/ (mrr_2026.csv + q1_review.pdf).
#     The tape doesn't regenerate these — see the Makefile / scripts to
#     produce them once. The CSV is committed under demo-data/ as a
#     reference; the PDF is generated locally via `cupsfilter`.

Output demo.gif

# Pure-black background, minimal colors. "Terminal on a dark page".
Set Theme { "name": "InClave", "background": "#000000", "foreground": "#e6e6e6", "cursor": "#e6e6e6", "selection": "#3a3a3a", "black": "#000000", "red": "#ff6b6b", "green": "#6ad673", "yellow": "#f0c674", "blue": "#7fb3ff", "magenta": "#c792ea", "cyan": "#7ce0e0", "white": "#e6e6e6", "brightBlack": "#5c5c5c", "brightRed": "#ff8787", "brightGreen": "#8ce28d", "brightYellow": "#ffd47e", "brightBlue": "#9ec4ff", "brightMagenta": "#dcb6ff", "brightCyan": "#a4ecec", "brightWhite": "#ffffff" }

Set FontSize 16
Set Width 1200
Set Height 760
Set Padding 22
Set TypingSpeed 40ms
Set Framerate 30
Set PlaybackSpeed 1.0

# --- setup (off-camera) ----------------------------------------------------
Hide
Type "cd ~/.inclave-demo && clear" Enter
Show

# --- the recorded demo -----------------------------------------------------
Sleep 600ms
Type "inclave"
Sleep 300ms
Enter
Sleep 4s

# Turn 1: ask a quantitative question over a CSV. Model writes Python,
# inclave runs it in the sandbox automatically, model summarizes.
# Phrasing is explicit ("print … using mrr_usd column") to keep the
# generated code on the happy path.
Type "~/.inclave-demo/mrr_2026.csv  print total mrr_usd growth in % from the first to the last row"
Sleep 400ms
Enter
Sleep 28s

# Turn 2: drop a PDF and ask for plain-text extraction. Phrasing tells
# the model "from this PDF" so it doesn't fall back to the CSV.
Type "~/.inclave-demo/q1_review.pdf  from this PDF, list the top 3 things that blocked Q1"
Sleep 400ms
Enter
Sleep 22s

Type "/exit"
Enter
Sleep 1500ms
