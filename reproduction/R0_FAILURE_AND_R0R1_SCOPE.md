# MSAHG official-sample R0 failure and R0R1 scope

## R0 failure

The first server invocation of commit
`3093dd52da10bbd1082869637394afc4965dd814` stopped before importing or
executing MSAHG because the server does not provide the external `unzip`
command:

```text
scripts/reproduce_official_sample_r0.sh: line 34: unzip: command not found
```

The partial R0 output is preserved at:

```text
/mnt/data4t/wyh/msahg_runs/msahg_official_sample_r0-3093dd52-gpu0
```

No model training, evaluation, or score-bearing result occurred in R0.

## R0R1 repair boundary

R0R1 changes only the reproduction wrapper's extraction mechanism from the
external `unzip` executable to Python's standard-library `zipfile` module.
The eight copied upstream Python sources, official `datasets/sample.zip`,
arguments, seed, model mathematics, optimizer, training loop, and evaluation
logic remain byte-identical to R0 and the frozen upstream commit
`3d74d70c852c56adcc09d907488410be5eda2744`.
