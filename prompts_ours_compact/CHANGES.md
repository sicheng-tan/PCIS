# prompts_ours → prompts_ours_compact (comparison, revised)

Path: `prompts_ours_compact/`. `user_prompt.txt` matches the original pack.

This revision follows feedback: **keep the original CoT reasoning structure + one important example set per section**; still drop the long Input tutorial and duplicated Requirements.

Experiment switch: `--strategy-mode default_simple` (aliases `ours_simple` / `simple`) → `folder_path=./prompts_ours_compact`, with the same template names as `default`.

## Size (approx.)

| File | Original words | Compact words | Reduction |
|------|----------------|---------------|-----------|
| equational `system_prompt.txt` | ~1343 | ~521 | ~61% |
| term_rewrite `system_prompt.txt` | ~1350 | ~505 | ~63% |

## vs original: removed / kept

| Block | Original | Compact |
|-------|----------|---------|
| Role | Long preamble | Short Role |
| Input tutorial | Three sections + line-by-line SMT walkthrough | **One short SMT structure example** (equational: Nat/plus; term_rewrite: Pow2) |
| **Chain of thoughts** | Full bullets + examples | **Full bullets kept**; examples trimmed to a critical subset (below) |
| Output skeleton | equational has `; The prove goal is :` etc. | **Kept** (equational); term_rewrite still XML |
| Requirements | Long list + multiple Examples + overlap with Output | Merged into **Rules**; keep one rule against copying the goal/ancestors |

## vs previous ultra-minimal compact: what was restored

| Restored | equational | term_rewrite |
|----------|------------|--------------|
| Full CoT structure | identify → simplify → base → IH step → rewrite simplify | pattern rewrite → restore bridges → subterm → strengthen → def facts |
| Critical examples | IH `(P (succ n))`; **qreva** generalization; **A2 + plus commutativity** stuck point | **Pow2/div pattern→p**; restore two bridges; **Pow2 i** subterm rewrite; premise strengthen / Q strengthen (short) |
| Output CoT template | `; Inductive proof` / `; Equational reasoning` skeleton | XML (same as original) |
| Small Input example | Nat + plus + negated goal | Pow2 + negated div goal |

## Still removed (vs original)

- Second Lst datatype walkthrough; natural-language restatement of the three-line plus asserts
- Long Example1–3 expansions under equational Requirements (one-line rules instead)
- term_rewrite **strengthen** examples that repeat the same Pow2 goal 3–4 times (CoT bullets kept; examples keep main rewrite + one subterm + short strategy notes)
- Boilerplate such as “You are good at extracting…”

## Risks

- Longer than the ultra-minimal pack, but still clearly shorter than the original.
- If accuracy drops, prefer restoring the original second Pow2 strengthen example in term_rewrite rather than the full Input tutorial.
