# Draft request to the MSAHG authors

Status: draft only; not sent.

Subject: Reproducibility materials for AAAI 2026 MSAHG

Dear authors,

We are independently reproducing *Multifaceted Scenario-Aware Hypergraph
Learning for Next POI Recommendation* from the official paper and repository.
We successfully executed the released NYC sample, but the repository does not
include the full datasets or a preprocessing pipeline sufficient to reconstruct
the paper tables.

Could you please provide or clarify the following materials?

1. The exact raw dataset source/version or immutable download identifiers for
   NYC, TKY, and Gowalla.
2. The complete preprocessing code and parameters that yield the user, POI,
   check-in, and trajectory counts reported in the paper.
3. The exact trajectory sessionization, minimum-length, label-construction,
   cold-start, and train/validation/test split rules.
4. The accommodation-category set and exact threshold/boundary rule used for
   local versus tourist labels.
5. The city-center coordinates and boundary convention used for the 10-km
   downtown/suburban labels.
6. Whether all hypergraphs are constructed strictly from training observations.
7. The seeds and aggregation protocol used for the reported metrics.
8. The intended APS conflict threshold (`-0.5` in the paper versus `-0.0001` in
   the released source), and the intended trigger schedule (every ten batches
   after the split epoch versus only two epochs in the released source).
9. The intended handling of task-specific parameter registration and optimizer
   membership after a split.
10. The intended validation/checkpoint procedure, since the released code uses
    `test.pkl` during training and for final evaluation.

One apparent dataset-identity issue also needs clarification. The paper reports
1,743 NYC users, while the public NYC/Tokyo Foursquare dataset page cited by
this research line reports about 1,082/1,083 NYC users. Please clarify whether a
different NYC source was used or whether the table contains a correction.

We will keep any engineering reconstruction explicitly separate from a
paper-table reproduction until these identities are resolved.

Sincerely,

Independent reproduction team
