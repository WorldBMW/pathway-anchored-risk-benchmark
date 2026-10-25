"""
downstream_genes.py — Shared gene-set definitions for post-training analyses.

Imported by BOTH:
  * scripts/train_st.py  (--dump_fused exports the spot×gene sub-matrix for the
                          union of these genes, so downstream scripts need no
                          re-alignment against raw Visium data), and
  * scripts/downstream_microenv.py / downstream_gsva_risk.py (scoring).

Single source of truth: do NOT redefine these gene lists inside the analysis
scripts, or the dumped column order and the scoring sets will drift apart.

All sets use HGNC symbols. Only genes present in the model's unified panel are
used (train_st.py intersects; analysis scripts re-intersect defensively).
"""

# ---------------------------------------------------------------------------
# 1) Cell-type marker sets (for microenvironment composition scoring).
#    Marker specificity is validated against the cervical scRNA-seq reference
#    (GSE308792, 31k cells) by downstream_microenv.py.
# ---------------------------------------------------------------------------
CELL_MARKERS = {
    "tumor_epithelial": ["KRT5", "KRT14", "KRT17", "KRT19", "KRT8", "KRT18",
                          "EPCAM", "TP63", "KRT6A", "KRT16"],
    "T_cell":      ["CD3D", "CD3E", "CD2", "CD8A", "CD4", "CD3G", "IL7R", "CCR7"],
    "B_cell":      ["CD79A", "MS4A1", "CD19", "CD79B", "BANK1"],
    "plasma":      ["MZB1", "JCHAIN", "SDC1", "IGKC"],
    "myeloid":     ["LYZ", "CD68", "CD14", "S100A8", "S100A9", "LST1",
                     "FCGR3A", "C1QA", "C1QB", "ITGAX"],
    "fibroblast":  ["COL1A1", "COL3A1", "DCN", "ACTA2", "COL1A2", "FAP",
                     "PDGFRB", "COL5A1"],
    "endothelial": ["VWF", "CLDN5", "PECAM1", "KDR", "EGFL7", "ENG"],
    "NK":          ["NKG7", "GNLY", "KLRD1", "KLRF1", "NCR1", "PRF1"],
}

# ---------------------------------------------------------------------------
# 2) Hallmark/KEGG-style pathway sets focused on HPV-driven cervical
#    carcinogenesis. Curated, compact (10-25 genes each, ssGSEA-appropriate).
# ---------------------------------------------------------------------------
PATHWAY_SETS = {
    "PROLIFERATION": ["MKI67", "PCNA", "TOP2A", "CCNB1", "CCND1", "CCNB2",
                       "CCNE1", "CDK1", "CDK2", "MCM2", "MCM3", "MCM4", "MCM5",
                       "MCM6", "BUB1", "AURKA", "AURKB", "FOXM1", "PLK1", "TYMS",
                       "UBE2C", "E2F1", "RRM2"],
    "EMT": ["VIM", "CDH2", "SNAI1", "SNAI2", "ZEB1", "ZEB2", "TWIST1", "FN1",
             "MMP2", "MMP9", "S100A4", "COL1A1", "COL3A1", "COL5A2", "TGFB1",
             "ACTA2", "ITGB1", "VCAN", "CDH1"],   # CDH1 = epithelial (anti-EMT)
    "INTERFERON_ANTIVIRAL": ["STAT1", "STAT2", "IRF1", "IRF7", "ISG15",
                              "IFIT1", "IFIT2", "IFIT3", "MX1", "MX2", "OAS1",
                              "OAS2", "OAS3", "IFI6", "IFI27", "IFI44", "IFI44L",
                              "RSAD2", "CXCL10"],
    "P53_PATHWAY": ["CDKN1A", "MDM2", "TP53", "BAX", "BBC3", "PMAIP1",
                     "GADD45A", "GADD45B", "SFN", "CCNG1", "SESN1", "ZMAT3"],
    "ANTIGEN_PRESENTATION": ["B2M", "HLA-A", "HLA-B", "HLA-C", "HLA-E",
                              "TAP1", "TAP2", "PSMB8", "PSMB9", "PSME2",
                              "CALR", "PDIA3"],
    "IMMUNE_CHECKPOINT": ["CD274", "PDCD1", "CTLA4", "IDO1", "LAG3", "TIGIT",
                           "HAVCR2", "PDCD1LG2", "SIGLEC15"],
    "HPV_INTEGRATION_CANDIDATE": ["CDKN2A", "MYC", "EGFR", "PIK3CA", "KRAS",
                                   "CCND1", "TP63", "PTEN", "AKT1", "MTOR"],
}

# 11 spatial permutation DEGs (FDR<0.05, all up-regulated in high-risk spots),
# from results/align_hpv_cervix35.json — layer3_cox.signature_genes.
SPATIAL_DEGS = ["KRT5", "B2M", "HLA-A", "KRT14", "HLA-C", "KRT19",
                "PSME2", "CCND1", "KRT17", "PTEN", "PSMB8"]


def downstream_gene_union():
    """Every gene we might score in the downstream analyses (deduped)."""
    u = set(SPATIAL_DEGS)
    for d in (CELL_MARKERS, PATHWAY_SETS):
        for v in d.values():
            u.update(v)
    return sorted(u)


def all_gene_sets():
    """One dict of {set_name: [genes]} for ssGSEA / enrichment scoring."""
    sets = {f"CELL_{k}": v for k, v in CELL_MARKERS.items()}
    sets.update(PATHWAY_SETS)
    return sets


if __name__ == "__main__":
    u = downstream_gene_union()
    print(f"downstream gene union: {len(u)} unique genes "
          f"({len(CELL_MARKERS)} cell types, {len(PATHWAY_SETS)} pathways, "
          f"{len(SPATIAL_DEGS)} spatial DEGs)")
