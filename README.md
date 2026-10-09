[README (3).md](https://github.com/user-attachments/files/33248587/README.3.md)
# Supplier Performance Scorecard & Procurement Risk Analysis

A procurement analytics project that evaluates supplier performance, highlights sourcing risks, and supports vendor review decisions through a KPI-based scorecard and Excel reporting views.

## Project Overview

Supplier decisions should consider more than unit price alone. This project combines six supplier KPIs into a structured scorecard, groups 50+ vendors into three risk tiers, flags suppliers requiring review, and tests whether supplier rankings remain stable when KPI weights change.

The outputs are designed to help procurement and sourcing teams compare suppliers consistently, understand the drivers behind each score, and prioritize corrective actions.

## Key Results

- Built a scorecard covering **50+ vendors** using **six KPIs**.
- Segmented suppliers into **three risk tiers** for prioritization.
- Identified **eight high-risk flags** for follow-up review.
- Tested ranking stability across **five weight scenarios**, perturbing KPI weights by **±10%**.
- Recorded an overall **Spearman rank correlation of 0.90**, indicating strong ranking consistency across the tested scenarios.
- Designed Excel views connecting supplier scores, risk tiers, KPI drivers, and recommended corrective actions.

## Business Questions

- Which suppliers are performing well across the selected KPIs?
- Which vendors should be prioritized for procurement or sourcing review?
- What KPI drivers contribute to a supplier's score or risk tier?
- Do small changes in KPI weights materially change supplier rankings?
- What corrective action should be considered for each flagged supplier?

## Methodology

### 1. KPI-based supplier scorecard

Supplier-level KPI values are standardized and combined using configurable weights to create a comparable supplier score. The scorecard should make the direction of each KPI explicit—for example, whether a higher value is better or worse—and apply consistent treatment to missing or invalid values.

> **KPI configuration:** Use the six KPIs defined in the project workbook or source data. Document their definitions, units, scoring direction, normalization approach, and baseline weights before interpreting the supplier scores. If the workbook uses a different KPI set, this README should be updated to match it.

### 2. Supplier risk tiers and flags

Suppliers are assigned to three risk tiers to support review prioritization. Eight high-risk flags are surfaced for further investigation. A flag should identify a specific rule or threshold that a supplier triggers; a flag indicates a review requirement, not proof that a supplier has failed or will fail.

### 3. Ranking sensitivity analysis

The baseline ranking is compared with five alternative weight scenarios in which KPI weights are varied by ±10%. Spearman rank correlation is used to measure how consistently suppliers are ordered under the different weighting assumptions. The project reports an overall correlation of **0.90** for the tested scenarios.

### 4. Excel reporting views

The Excel views link the overall supplier score to risk tier, KPI-level drivers, and suggested corrective actions. This makes it easier for procurement stakeholders to move from a vendor ranking to the reasons behind that ranking and the next review step.

## Suggested Workbook Structure

The exact sheet names can be adapted to the workbook. A practical structure is:

| Sheet | Purpose |
|---|---|
| `Supplier_Data` | Vendor-level source data and KPI values |
| `KPI_Weights` | KPI definitions, directions, normalization rules, and weights |
| `Supplier_Scorecard` | Standardized KPI scores and overall supplier scores |
| `Risk_Analysis` | Risk tiers and the eight high-risk flags |
| `Sensitivity_Analysis` | Five weight scenarios and rank-correlation results |
| `Dashboard` | Filters and summary views for procurement review |
| `Action_Plan` | Flagged suppliers, KPI drivers, owners, and corrective actions |

## Recommended Dashboard Metrics

- Number of suppliers evaluated
- Supplier distribution by risk tier
- Highest- and lowest-scoring suppliers
- KPI-level performance comparisons
- Count of high-risk flags
- Supplier ranking changes across weight scenarios
- Spearman rank correlation by scenario
- Corrective actions open, in progress, and completed (if action-tracking data is available)

## How to Use

1. Review the KPI definitions and scoring directions.
2. Confirm that the weights and normalization rules match the workbook methodology.
3. Refresh supplier data and recalculate scores and risk tiers.
4. Review high-risk flags and the KPI drivers behind each flag.
5. Examine the sensitivity analysis before making decisions based on close supplier rankings.
6. Use the Excel views to record follow-up questions and corrective actions.

## Tools

- **Microsoft Excel** — scorecard calculations, sensitivity scenarios, filters, and reporting views.
- **Supplier KPI data** — vendor-level inputs used to calculate performance and risk indicators.

## Assumptions and Limitations

- Supplier scores depend on the quality, completeness, and timeliness of the input data.
- KPI normalization, weight selection, tier thresholds, and high-risk rules can affect the resulting scorecard; these rules should be documented in the workbook.
- A Spearman correlation of 0.90 indicates strong rank agreement in the tested scenarios, but it does not establish that the weights or supplier ratings are objectively correct.
- High-risk flags are review signals and should be checked against procurement context before action is taken.
- The scorecard supports procurement judgment; it should not replace due diligence, contract review, or supplier discussions.

## Repository Contents

Add the workbook and any supporting files to this repository, for example:

```text
supplier-performance-scorecard/
├── README.md
├── data/                 # Supplier data, with confidential fields removed
├── workbook/             # Excel scorecard and reporting views
└── docs/                 # KPI definitions and methodology notes
```

Only include data that you are authorized to share. Remove confidential supplier names, prices, contract terms, and other sensitive information before publishing a public repository.

## Resume Summary

Developed an Excel-based supplier scorecard for 50+ vendors using six KPIs, three risk tiers, eight high-risk flags, and five ±10% weight scenarios; assessed ranking stability with a 0.90 Spearman correlation.
