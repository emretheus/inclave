# Demo data

Sample files used by `demo.tape` (the `vhs` recording that produces `demo.gif`).

- `mrr_2026.csv` — 8 months of fictional SaaS metrics (signups, churn, MRR).
- `q1_review.pdf` — fictional Q1 engineering retrospective.

Both are synthetic. They live here so `demo.tape` is reproducible without a
side-channel data setup step.

## Regenerating demo.gif

```bash
brew install vhs
uv tool install --force --from packages/cli inclave-cli
ollama serve &
ollama pull qwen2.5-coder:7b  # ~4.4 GB; the recording sets this as default

# Copy the demo data into the workdir the tape expects:
mkdir -p ~/.inclave-demo
cp demo-data/*.csv demo-data/*.pdf ~/.inclave-demo/

# Optional: wipe leftover workspace state for a clean run.
rm -rf ~/.inclave/workspaces ~/.inclave/sessions

vhs demo-data/demo.tape   # writes demo-data/demo.gif
```
