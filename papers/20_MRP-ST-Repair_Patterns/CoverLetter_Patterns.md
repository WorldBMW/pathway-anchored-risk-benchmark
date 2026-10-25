# Cover letter

25 October 2026

Dear Editors of Patterns,

Please consider our manuscript, "Auditing label dependence and sibling-unit inflation in group-structured representations," as a Research Article.

**Why this is a Patterns paper and not a spatial-transcriptomics paper.** Whenever a group contributes more than one observation to a data set, an evaluation split drawn at the observation level silently preserves group identity, and a model can satisfy its objective by recognizing the group rather than the target property. That failure is not specific to any single field: it has been reported separately in clinical machine learning, wearable sensing, ecology and brain imaging, each time as a reproducibility incident and each time patched case by case rather than measured. What is missing across those literatures is not another removal operator but an instrument: a calibrated statistic that says, after any attempt to remove group identity, whether what remains still transfers across groups and whether it exceeds what permutation alone would produce. The deliverable in this paper is that measurement and the decision boundary it induces, not a model and not a domain result. Spatial transcriptomics is where we can validate it end to end, because it supplies planted controls and ordinal donor-level labels; we treat it as a demanding testbed, not as the subject of the paper. The remaining cohorts are deliberately presented as prediction tests of that boundary rather than as demonstrations of repair utility, and the paper says so.

**What the paper establishes, in one paragraph.** A controlled simulation shows unit-level label association remaining high after group-level transfer deteriorates. A fixed-scale interval inequality states when requiring both low label dependence and retention of that same association is contradictory; it is a compatibility condition on two numbers, not a guarantee that any intervention reaches a feasible point. The repair operator is standard and deliberately so, suppression is partial, and no accepted repair in our results improved a downstream endpoint. We report this as an audit and a negative result on repair utility, not as a validated remediation.

**Scope limits we state in the paper.** Cross-domain rank metrics depend on nominal-label coding, and the archived multi-unit permutation scheme is not group-preserving, so the reported gate is not presented as a group-level 5% test. Donor and patient identifiers are not resolved for every cohort, so we do not claim patient-disjoint generalization. We therefore re-ran six of these items rather than leaving them as caveats: a group-preserving permutation null on every multi-unit cohort (which moves the null scale by 0–49% depending on the group-label coupling, and is undefined where the label is constant within group), separate identity-decoding and nominal multiclass readouts, a frozen-baseline scale convention, a reconstructed cervical donor map, an enumeration of all 21 possible GeoMx patient pairings, and an outer-loop refit on the one cohort where refitting the encoder per fold was affordable. No gate decision changes under any of them.

**Related manuscript.** In line with the Cell Press policy on related manuscripts, we disclose a related manuscript by the same group and supply it with this submission as a related file. It also develops a label-dependence index and draws on overlapping public cervical accessions. It is not cited anywhere in this manuscript, and no result, table or figure is shared: every number reported here was recomputed by us from the public accessions listed in the key resources table.

**Data and code.** All cohorts are public accessions re-downloaded by the released scripts. The code is released under the tagged state v1.0.0 at https://github.com/WorldBMW/pathway-anchored-risk-benchmark and is archived in Zenodo at https://doi.org/10.5281/zenodo.23640979.

**Declarations.** The authors declare no competing interests. AI-assisted tools were used for editorial and language preparation, and the use is declared in the manuscript; no tool generated algorithmic logic or experimental results, and the authors take full responsibility for the content.

Sincerely,

Lang Guo, on behalf of the authors

School of Pharmacy, Shenyang Medical College, Shenyang 110034, China

guolang1016@symc.edu.cn
