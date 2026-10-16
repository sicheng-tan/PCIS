# Appendix A — Excluded instances (known non-theorems)

Twenty benchmark tasks are excluded from the evaluation suite because, under
the current SMT encodings/axioms, the stated goals are **not theorems**.
These are encoding defects (or intentionally false crafted goals), not
failures of the proof method.

Skip file: `experiments/configs/skip_nontheorems.txt`.

## Summary (20 instances)

| # | Path | Family / root cause |
|---|------|---------------------|
| 1 | `ind-ben/list/crafted_assorted/2` | Goal binds the wrong list in the conclusion |
| 2 | `ind-ben/list/crafted_assorted/3` | Shared buggy `cnt` axiom (`e≠x` recurses on `e`) |
| 3 | `ind-ben/list/crafted_assorted/6` | Same `cnt` bug |
| 4 | `ind-ben/list/crafted_assorted/15` | Same `cnt` bug |
| 5 | `ind-ben/list/crafted_assorted/17` | Same `cnt` bug |
| 6 | `ind-ben/list/crafted_assorted/19` | Same `cnt` bug |
| 7 | `ind-ben/tree/crafted_rotate/10` | Full-spine rotate pair is not inverse |
| 8 | `ind-ben/tree/crafted_rotate/11` | Same rotate encoding |
| 9 | `dtt/dtt-leon/bsearch-tree-goal4` | `less` unconstrained on negatives |
| 10 | `dtt/dtt-leon/bsearch-tree-goal5` | Same `less` gap |
| 11 | `dtt/dtt-leon/bsearch-tree-goal8` | Same `less` gap |
| 12 | `dtt/dtt-leon/bsearch-tree-goal11` | Same `less` gap |
| 13 | `dtt/dtt-leon/bsearch-tree-goal14` | Same `less` gap |
| 14 | `dtt/dtt-leon/bsearch-tree-goal17` | Same `less` gap |
| 15 | `vmcai15-dt/leon/heap-goal11` | `heapsort` vs ascending `sorted` mismatch |
| 16 | `vmcai15-dt/isa/goal75` | Known non-theorem under current axioms |
| 17 | `dtt/dtt-isa/goal74` | `drop`/`minus` free on negatives |
| 18 | `dtt/dtt-isa/goal76` | `take`/`minus` free on negatives |
| 19 | `dtt/dtt-isa/goal79` | `less` only constrained for nonnegatives |
| 20 | `dtt/dtt-isa/goal80` | Same `less` gap as goal79 |

## Notes

- Paths above are under `benchmarks/preprocessed/…` in the skip file.
- Counterexample audits for the first 16 appear in historical analysis of
  root `INVALID_GOAL` claims; the four `dtt-isa` goals were confirmed in a
  later audit and added so they are not counted as method failures.
