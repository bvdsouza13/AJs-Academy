"""2026–27 published budgets retrieved 2026-10-11. Planning inputs, not live quotes."""
BASELINES = {
    "Stanford": (97545, 97545, "Published total excludes travel; add family travel and first-year fees ($775). Health insurance may be extra."),
    "MIT": (92760, 92760, "Published total excludes location-specific travel and health insurance; add those if needed."),
    "Harvard": (95134, 95134, "Lower end of published $95,134–$100,134 range. Add travel up to $5,000 and insurance if not waived."),
    "UC Berkeley": (93944, 54674, "On-campus total $54,674; nonresidents add $39,270. Includes university health insurance."),
    "UCLA": (84770, 45500, "Published new-student on-campus total, including university health insurance."),
    "University of Florida": (25830, 54010, "Published on/off-campus total; Florida in-state vs California out-of-state. Tuition estimates may change."),
    "UC San Diego": (86553, 47283, "Published 2026-cohort on-campus total, including university health insurance."),
    "San Diego State": (53562, 36432, "Published on-campus annual total; nonresident budget assumes 30 units."),
    "University of San Diego": (98418, 98418, "Sum of tuition $64,100, fees $1,099, insurance $4,158, average campus housing $14,042, food $8,344, personal $3,969, travel $1,386, books $1,320."),
}

def baseline(name, residency):
    florida, california, note = BASELINES[name]
    return {"annual": florida if residency == "Florida" else california,
            "note": "2026–27 official university budget. " + note,
            "updated": "2026-10-11", "travel": 0., "extras": 0.}
