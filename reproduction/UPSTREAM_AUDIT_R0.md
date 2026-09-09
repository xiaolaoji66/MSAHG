# MSAHG AAAI 2026 — Upstream Reproduction Audit R0

## Reproduction authority

- Paper: *Multifaceted Scenario-Aware Hypergraph Learning for Next POI Recommendation* (AAAI 2026)
- Official repository: `https://github.com/COCOMiss/MSAHG`
- Frozen upstream branch: `main`
- Frozen upstream commit: `3d74d70c852c56adcc09d907488410be5eda2744`
- License: MIT

This reproduction project is independent of GUGEN. No GUGEN, CIPRA, or prior
experimental implementation is an input to R0.

## What R0 can establish

R0 is a source-exact replay of the released NYC sample. It may establish that
the published Python implementation can build its released sample graphs,
train, evaluate, and emit a complete receipt on a qualified server.

R0 cannot reproduce the paper's Table 1 because the released sample and paper
dataset are not identical:

- released sample NYC: 159 users and 6,870 POIs;
- paper/README NYC: 1,743 users and 7,289 POIs.

The repository contains no complete NYC/TKY/Gowalla processed datasets and no
raw-data preprocessing pipeline that can reconstruct the paper inputs.

## Upstream inconsistencies preserved as evidence

1. README invokes `main.py`; no such file exists in any current branch. The
   executable current source is `run.py`.
2. README asks for `requirements.txt`; the file is absent.
3. `sample.sh` invokes `run_nash_divide.py`; it is absent from `main` but is
   present on the historical `master` branch. Current `run.py` is the later
   MSAHG entrypoint.
4. README says Python 3.12+, while `environment.yml` pins Python 3.8.20.
5. `utils.py` imports DGL and `adaptive_par.py` imports CVXPY, but neither is
   declared by `environment.yml`.
6. The paper states Adam weight decay `5e-4`; `run.py` parses `--decay` but does
   not pass it to Adam.
7. The paper states a gradient-conflict threshold below `-0.5`; released source
   uses `< -0.0001`.
8. The paper states conflict checks every 10 training batches after the split
   epoch. Released source only enters splitting at `divide_epoch` and
   `divide_epoch + 10`, accumulating the first configured batches.
9. `run.py` uses `test.pkl` for epoch-by-epoch checkpoint selection and then
   evaluates the selected checkpoint on the same `test.pkl`. Therefore its
   emitted final score is test-selected and is not an independent test result.
10. Training and evaluation repeatedly call `next(iter(dataloader))`, creating
    a fresh iterator for every step rather than consuming one epoch iterator.

These observations mean "official-code replay" and "paper-faithful
reproduction" must remain separate claims.

## R0 execution boundary

- Preserve all upstream Python files byte-for-byte.
- Use only `datasets/sample.zip`.
- Execute `run.py` through the additive wrapper in
  `scripts/reproduce_official_sample_r0.sh`.
- Report Acc@1/5/10/20 and MRR as sample-replay diagnostics only.
- Do not compare the sample score mechanically with Table 1.
- Do not repair mathematics, data iteration, parameter splitting, checkpoint
  selection, or evaluation semantics inside R0.

## R1 paper-aligned status

R1 is blocked pending complete processed datasets or a separately audited
preprocessing reconstruction. Any R1 repair must be versioned independently
and must never overwrite the R0 result.
