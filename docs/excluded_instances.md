# Excluded instances (706 → 686)

The original collection has **706** SMT-LIB tasks. We exclude **20** instances
whose goals are **not entailed** by their encoded axioms, leaving **686** for
evaluation. None of the excluded instances was proved by the evaluated methods.
Exclusions follow counterexamples or interpretations permitted by the encodings
(paper Appendix A).

Breakdown: **2** StandardDT (`vmcai15-dt`), **10** StandardDTLIA (`dtt`),
**0** AutoProofBM, **8** IndBen (`ind-ben`).

Machine-readable paths: `experiments/configs/skip_nontheorems.txt`.

---

## IndBen — list counting (`ind-ben/list/crafted_assorted`)

The nonmatching branch of `cnt` changes the queried element
(`e ≠ x ⇒ cnt(cons(e,t), x) = cnt(t, e)`), so it is not ordinary occurrence count.

| Path | Reason (witness sketch) |
|------|-------------------------|
| `.../crafted_assorted/2` | Premise: `e` at index `i` in `x`; conclusion: positive count in another list `l`. `e=i=0`, `x=[0]`, `l=[]`. |
| `.../crafted_assorted/3` | Equal counts for every element ⇒ equal lengths. `l1=[0,1]`, `l2=[0]` share encoded counts but differ in length. |
| `.../crafted_assorted/6` | Reversal preserves counts. For `xs=[0,1,2]`, `cnt(xs,0)=1` but `cnt(rev(xs),0)=0`. |
| `.../crafted_assorted/15` | Unequal lists differ in some count. `[0]` and `[0,1]` are unequal yet match on every encoded count. |
| `.../crafted_assorted/17` | Every count in an even-length palindrome is even. `[0,0]` is such a palindrome but `cnt([0,0],1)=1`. |
| `.../crafted_assorted/19` | At most one element with odd count in a palindrome. For `[0,0]`, both `cnt(_,1)` and `cnt(_,2)` are 1. |

## IndBen — tree rotations (`ind-ben/tree/crafted_rotate`)

`rotateLeft` / `rotateRight` repeatedly rotate until an outer child is empty; they
are not single mutually inverse rotations. With
`tL = N(N(E,0,E),1,E)` and `tR = N(E,0,N(E,1,E))`:

| Path | Reason |
|------|--------|
| `.../crafted_rotate/10` | `rotateLeft(rotateRight(tR)) ≠ tR` |
| `.../crafted_rotate/11` | `rotateRight(rotateLeft(tL)) ≠ tL` |

## StandardDTLIA — BST `less` (`dtt/dtt-leon/bsearch-tree-goal*`)

`less` is constrained only for nonnegative arguments
(`x≥0 ∧ y≥0 ⇒ (less(x,y) ↔ x<y)`), while tree values range over all integers.

| Path | Reason (sketch) |
|------|-----------------|
| `.../bsearch-tree-goal4` | Negatives make both comparison branches fail; `tremove` size bound fails. |
| `.../bsearch-tree-goal5` | Same encoding gap for repeated removal size bound. |
| `.../bsearch-tree-goal8` | Insertion with negatives can violate `tsorted`. |
| `.../bsearch-tree-goal11` | `tmember` / content equivalence fails under a permitted `less` on negatives. |
| `.../bsearch-tree-goal14` | `tinsert-all` can produce an unsorted tree from `[-1,-5]`. |
| `.../bsearch-tree-goal17` | Same membership gap as goal11 under another `less` interpretation. |

## StandardDTLIA — Int indices / sort (`dtt/dtt-isa`)

| Path | Reason |
|------|--------|
| `.../goal74` | `drop` / `minus` only axiomatized for nonnegative indices; goal quantifies all `Int`. CE: `i=-1`, `xs=[0]`. |
| `.../goal76` | Symmetric for `take` / `minus`. CE: `i=-1`, `xs=[1]`. |
| `.../goal79` | `less` only constrained on nonnegative; `insort(-1,[0])` need not be sorted. |
| `.../goal80` | Same `less` gap; `sort([-1,-2])` need not be ordered. |

## StandardDT — heap / unconstrained filter (`vmcai15-dt`)

| Path | Reason |
|------|--------|
| `.../leon/heap-goal11` | Natural comparison as usual `<` extracts max first; `heapsort([0,1])=[1,0]` fails encoded `sorted`. |
| `.../isa/goal75` | `filter` declared with no defining axioms; constant `filter≡[0,1]` refutes `rev(filter(xs))=filter(rev(xs))`. |
