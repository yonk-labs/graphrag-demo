"""
Generates a synthetic SCOTUS-style dataset for the GraphRAG demo.

Designed so that structural queries (voting patterns, citation chains,
which-justice-dissented-on-what) require graph traversal. The information
needed to answer those queries deliberately does NOT live in document text.
"""

import json
import random

from seed.scotus_templates import (
    SUMMARY_TEMPLATES,
    MAJORITY_OPINION_TEMPLATES,
    DISSENT_TEMPLATES,
    PETITIONER_ARGS,
    RESPONDENT_ARGS,
    LEGAL_QUESTIONS,
    HOLDINGS,
    DOCTRINES,
    LOWER_COURT_OUTCOMES,
    DISSENT_COUNTERS,
    PRECEDENT_REFERENCES,
    DISPOSITIONS,
    CRITIQUES,
    FRAMINGS,
    HISTORICAL_CLAIMS,
    ALTERNATIVE_OUTCOMES,
    BROADER_IMPACTS,
)

# Dedicated RNG so importing this module doesn't perturb the Acme generator,
# which uses the module-global random with seed 42.
_rng = random.Random(43)


# --- Justices (20, spanning ~1972-2030) ---
JUSTICES = [
    {"id": "j-roberts",    "name": "John Roberts",       "active_start": 2005, "active_end": 2030, "lean": "conservative"},
    {"id": "j-thomas",     "name": "Clarence Thomas",    "active_start": 1991, "active_end": 2030, "lean": "conservative"},
    {"id": "j-alito",      "name": "Samuel Alito",       "active_start": 2006, "active_end": 2030, "lean": "conservative"},
    {"id": "j-gorsuch",    "name": "Neil Gorsuch",       "active_start": 2017, "active_end": 2030, "lean": "conservative"},
    {"id": "j-kavanaugh",  "name": "Brett Kavanaugh",    "active_start": 2018, "active_end": 2030, "lean": "conservative"},
    {"id": "j-barrett",    "name": "Amy Coney Barrett",  "active_start": 2020, "active_end": 2030, "lean": "conservative"},
    {"id": "j-sotomayor",  "name": "Sonia Sotomayor",    "active_start": 2009, "active_end": 2030, "lean": "liberal"},
    {"id": "j-kagan",      "name": "Elena Kagan",        "active_start": 2010, "active_end": 2030, "lean": "liberal"},
    {"id": "j-jackson",    "name": "Ketanji Brown Jackson", "active_start": 2022, "active_end": 2030, "lean": "liberal"},
    {"id": "j-ginsburg",   "name": "Ruth Bader Ginsburg","active_start": 1993, "active_end": 2020, "lean": "liberal"},
    {"id": "j-breyer",     "name": "Stephen Breyer",     "active_start": 1994, "active_end": 2022, "lean": "liberal"},
    {"id": "j-scalia",     "name": "Antonin Scalia",     "active_start": 1986, "active_end": 2016, "lean": "conservative"},
    {"id": "j-kennedy",    "name": "Anthony Kennedy",    "active_start": 1988, "active_end": 2018, "lean": "moderate"},
    {"id": "j-stevens",    "name": "John Paul Stevens",  "active_start": 1975, "active_end": 2010, "lean": "liberal"},
    {"id": "j-souter",     "name": "David Souter",       "active_start": 1990, "active_end": 2009, "lean": "moderate"},
    {"id": "j-oconnor",    "name": "Sandra Day O'Connor","active_start": 1981, "active_end": 2006, "lean": "moderate"},
    {"id": "j-rehnquist",  "name": "William Rehnquist",  "active_start": 1972, "active_end": 2005, "lean": "conservative"},
    {"id": "j-marshall",   "name": "Thurgood Marshall",  "active_start": 1967, "active_end": 1991, "lean": "liberal"},
    {"id": "j-brennan",    "name": "William Brennan",    "active_start": 1956, "active_end": 1990, "lean": "liberal"},
    {"id": "j-powell",     "name": "Lewis Powell",       "active_start": 1972, "active_end": 1987, "lean": "moderate"},
]


# --- Issues (15) ---
ISSUES = [
    {"id": "iss-first-amend",    "name": "First Amendment",   "category": "constitutional"},
    {"id": "iss-fourth-amend",   "name": "Fourth Amendment",  "category": "constitutional"},
    {"id": "iss-antitrust",      "name": "Antitrust",         "category": "commercial"},
    {"id": "iss-environmental",  "name": "Environmental Law", "category": "regulatory"},
    {"id": "iss-civil-rights",   "name": "Civil Rights",      "category": "constitutional"},
    {"id": "iss-immigration",    "name": "Immigration",       "category": "regulatory"},
    {"id": "iss-criminal-proc",  "name": "Criminal Procedure","category": "constitutional"},
    {"id": "iss-admin-law",      "name": "Administrative Law","category": "regulatory"},
    {"id": "iss-patent",         "name": "Patent Law",        "category": "commercial"},
    {"id": "iss-tax",            "name": "Tax Law",           "category": "commercial"},
    {"id": "iss-labor",          "name": "Labor Law",         "category": "regulatory"},
    {"id": "iss-commerce",       "name": "Commerce Clause",   "category": "constitutional"},
    {"id": "iss-federalism",     "name": "Federalism",        "category": "constitutional"},
    {"id": "iss-due-process",    "name": "Due Process",       "category": "constitutional"},
    {"id": "iss-voting-rights",  "name": "Voting Rights",     "category": "constitutional"},
]


# --- Case name parts ---
PLAINTIFF_TYPES = [
    "United States", "State of California", "State of Texas", "Apple",
    "Microsoft", "Smith", "Johnson", "Doe", "EPA", "FCC", "City of Chicago",
    "Acme Corp", "National Federation of Independent Business", "Google",
    "Amazon", "NLRB", "SEC", "FTC", "Roe", "Citizens United",
]

DEFENDANT_TYPES = [
    "Pepper", "Arkansas", "Department of Commerce", "FDA", "EPA",
    "Lopez", "Brown", "Jones", "Miller", "Wade", "Sebelius",
    "Virginia", "Massachusetts", "Board of Education", "City of New York",
    "Secretary of Labor", "Commissioner", "Harper", "Hogan", "Bruen",
]


OUTCOMES = [
    "affirmed", "reversed", "reversed and remanded", "vacated and remanded",
    "affirmed in part and reversed in part",
]


def _generate_case_name():
    p = _rng.choice(PLAINTIFF_TYPES)
    d = _rng.choice(DEFENDANT_TYPES)
    return f"{p} v. {d}"


def _pick_vote_split():
    return _rng.choices(
        ["5-4", "6-3", "7-2", "8-1", "9-0"],
        weights=[30, 25, 15, 10, 20],
    )[0]


def _assign_votes(court, vote_split):
    """Assign majority/dissent votes for `court` (a list of justices) biased
    by ideological lean.

    Returns dict justice_id -> "majority" | "dissent".
    """
    maj_count, diss_count = map(int, vote_split.split("-"))
    total = maj_count + diss_count

    # Randomly decide which lean controls the majority this case.
    controlling_lean = _rng.choice(["conservative", "liberal"])

    def score(j):
        # Higher score = more likely to be in majority.
        base = {
            "conservative": 1.0 if controlling_lean == "conservative" else 0.0,
            "liberal":      1.0 if controlling_lean == "liberal" else 0.0,
            "moderate":     0.5,
        }[j["lean"]]
        # Add jitter so 9-0 and crossover cases happen naturally.
        return base + _rng.random() * 0.7

    ordered = sorted(court[:total], key=score, reverse=True)
    votes = {}
    for j in ordered[:maj_count]:
        votes[j["id"]] = "majority"
    for j in ordered[maj_count:total]:
        votes[j["id"]] = "dissent"
    return votes


def _select_court_for_term(term):
    """Return 9 justices active in `term`. If fewer than 9 active, pad with
    whoever is closest in tenure so the term always has a full bench."""
    active = [j for j in JUSTICES if j["active_start"] <= term <= j["active_end"]]
    if len(active) >= 9:
        return _rng.sample(active, 9)
    # Pad with nearest-in-time justices
    remaining = [j for j in JUSTICES if j not in active]
    remaining.sort(key=lambda j: min(abs(j["active_start"] - term), abs(j["active_end"] - term)))
    return active + remaining[: 9 - len(active)]


def generate_cases(n=150):
    cases = []
    for i in range(n):
        term = _rng.randint(2000, 2023)
        court = _select_court_for_term(term)

        vote_split = _pick_vote_split()
        votes = _assign_votes(court, vote_split)

        majority_ids = [jid for jid, v in votes.items() if v == "majority"]
        dissent_ids = [jid for jid, v in votes.items() if v == "dissent"]

        majority_author = _rng.choice(majority_ids)
        dissent_author = _rng.choice(dissent_ids) if dissent_ids else None

        # A handful of concurrences
        concurring_ids = []
        if len(majority_ids) >= 3 and _rng.random() < 0.2:
            concurring_ids = [_rng.choice([m for m in majority_ids if m != majority_author])]

        case = {
            "id": f"case-{i:04d}",
            "name": _generate_case_name(),
            "docket": f"{term - 2000:02d}-{_rng.randint(100, 999)}",
            "term": term,
            "year": term,
            "citation": f"{_rng.randint(500, 600)} U.S. {_rng.randint(1, 999)}",
            "outcome": _rng.choice(OUTCOMES),
            "issue_ids": _rng.sample([iss["id"] for iss in ISSUES], k=_rng.randint(1, 3)),
            "votes": votes,
            "concurring_ids": concurring_ids,
            "majority_author": majority_author,
            "dissent_author": dissent_author,
            "vote_split": vote_split,
        }
        cases.append(case)
    return cases


def generate_citations(cases):
    """Build a citation network. Later cases cite earlier cases only."""
    citations = []
    for case in cases:
        earlier = [c for c in cases if c["term"] < case["term"]]
        if not earlier:
            continue
        k = min(_rng.randint(2, 5), len(earlier))
        cited = _rng.sample(earlier, k)
        for c in cited:
            citations.append({"from_id": case["id"], "to_id": c["id"]})
    return citations


def _justice_by_id(jid):
    return next(j for j in JUSTICES if j["id"] == jid)


def _issue_by_id(iid):
    return next(i for i in ISSUES if i["id"] == iid)


def generate_documents(cases):
    """3 documents per case: summary, majority opinion, and dissent (if split).

    The summary names the case and parties (vector-friendly).
    The opinion and dissent avoid naming the case or specific justices, so
    questions like "who dissented in antitrust cases" cannot be answered from
    text alone — the graph must fill that gap.
    """
    docs = []
    doc_id = 0
    for case in cases:
        primary_issue = _issue_by_id(case["issue_ids"][0])["name"]
        majority_justice = _justice_by_id(case["majority_author"])
        dissent_clause = ""
        if case["dissent_author"]:
            dj = _justice_by_id(case["dissent_author"])
            dissent_clause = f"Justice {dj['name']} filed a dissenting opinion."

        # --- Summary (names case) ---
        s_title_t, s_content_t = _rng.choice(SUMMARY_TEMPLATES)
        s_repl = {
            "case_name": case["name"],
            "term": case["term"],
            "issue": primary_issue,
            "vote_split": case["vote_split"],
            "outcome": case["outcome"],
            "majority_author": majority_justice["name"],
            "dissent_author_clause": dissent_clause,
            "petitioner_arg": _rng.choice(PETITIONER_ARGS),
            "respondent_arg": _rng.choice(RESPONDENT_ARGS),
        }
        docs.append({
            "id": f"scotus-doc-{doc_id:04d}",
            "title": s_title_t.format(**s_repl),
            "content": s_content_t.format(**s_repl),
            "doc_type": "case_summary",
            "author_id": case["majority_author"],
            "project_id": case["id"],
            "dataset": "scotus",
            "created_at": f"{case['term']}-06-15",
        })
        doc_id += 1

        # --- Majority opinion (title names case; body does NOT) ---
        _m_title_t, m_content_t = _rng.choice(MAJORITY_OPINION_TEMPLATES)
        m_repl = {
            "legal_question": _rng.choice(LEGAL_QUESTIONS),
            "holding": _rng.choice(HOLDINGS),
            "doctrine": _rng.choice(DOCTRINES),
            "lower_court_outcome": _rng.choice(LOWER_COURT_OUTCOMES),
            "dissent_counter": _rng.choice(DISSENT_COUNTERS),
            "precedent_reference": _rng.choice(PRECEDENT_REFERENCES),
            "disposition": _rng.choice(DISPOSITIONS),
        }
        docs.append({
            "id": f"scotus-doc-{doc_id:04d}",
            "title": f"{case['name']}: Majority Opinion",
            "content": m_content_t.format(**m_repl),
            "doc_type": "majority_opinion",
            "author_id": case["majority_author"],
            "project_id": case["id"],
            "dataset": "scotus",
            "created_at": f"{case['term']}-06-15",
        })
        doc_id += 1

        # --- Dissent (title names case; body does NOT) ---
        if case["dissent_author"]:
            _d_title_t, d_content_t = _rng.choice(DISSENT_TEMPLATES)
            d_repl = {
                "critique": _rng.choice(CRITIQUES),
                "framing_majority": _rng.choice(FRAMINGS),
                "framing_dissent": _rng.choice(FRAMINGS),
                "historical_claim": _rng.choice(HISTORICAL_CLAIMS),
                "alternative_outcome": _rng.choice(ALTERNATIVE_OUTCOMES),
                "broader_impact": _rng.choice(BROADER_IMPACTS),
                "precedent_ref": _rng.choice(PRECEDENT_REFERENCES),
            }
            docs.append({
                "id": f"scotus-doc-{doc_id:04d}",
                "title": f"{case['name']}: Dissent",
                "content": d_content_t.format(**d_repl),
                "doc_type": "dissent",
                "author_id": case["dissent_author"],
                "project_id": case["id"],
                "dataset": "scotus",
                "created_at": f"{case['term']}-06-16",
            })
            doc_id += 1
    return docs


def generate_all():
    cases = generate_cases()
    citations = generate_citations(cases)
    documents = generate_documents(cases)
    return {
        "justices": JUSTICES,
        "issues": ISSUES,
        "cases": cases,
        "citations": citations,
        "documents": documents,
    }


if __name__ == "__main__":
    data = generate_all()
    print(json.dumps(data, indent=2, default=str))
    print(
        f"\nGenerated: {len(data['cases'])} cases, "
        f"{len(data['justices'])} justices, "
        f"{len(data['issues'])} issues, "
        f"{len(data['documents'])} documents, "
        f"{len(data['citations'])} citations"
    )
