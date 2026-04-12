"""
Parses real SCOTUS case markdown files into the GraphRAG demo dataset.
Source files: /home/yonk/yonk-tools/pg-raggraph/benchmarks/scotus/ (391 cases, 2018-2023 terms)
"""

import os
import re
from pathlib import Path

_DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "scotus",
)
SCOTUS_SOURCE_DIR = os.environ.get("SCOTUS_SOURCE_DIR", _DEFAULT_DATA_DIR)

# --- Issue taxonomy (hand-curated keyword-based classification) ---
ISSUE_KEYWORDS = {
    "iss-first-amend": {
        "name": "First Amendment",
        "keywords": ["first amendment", "free speech", "free exercise", "establishment clause", "religious", "free press"],
    },
    "iss-fourth-amend": {
        "name": "Fourth Amendment",
        "keywords": ["fourth amendment", "search and seizure", "warrant", "probable cause", "unreasonable search"],
    },
    "iss-antitrust": {
        "name": "Antitrust",
        "keywords": ["antitrust", "sherman act", "clayton act", "monopoly", "monopolization", "restraint of trade"],
    },
    "iss-criminal": {
        "name": "Criminal Procedure",
        "keywords": ["criminal", "sentencing", "miranda", "double jeopardy", "habeas", "capital punishment", "death penalty"],
    },
    "iss-civil-rights": {
        "name": "Civil Rights",
        "keywords": ["civil rights", "discrimination", "equal protection", "title vii", "ada", "section 1983"],
    },
    "iss-immigration": {
        "name": "Immigration",
        "keywords": ["immigration", "deportation", "asylum", "alien", "naturalization", "removal"],
    },
    "iss-admin-law": {
        "name": "Administrative Law",
        "keywords": ["administrative", "agency", "chevron", "rulemaking", "apa", "administrative procedure"],
    },
    "iss-due-process": {
        "name": "Due Process",
        "keywords": ["due process", "procedural", "substantive due process", "liberty interest"],
    },
    "iss-commerce": {
        "name": "Commerce Clause",
        "keywords": ["commerce clause", "interstate commerce", "dormant commerce"],
    },
    "iss-federalism": {
        "name": "Federalism",
        "keywords": ["federalism", "tenth amendment", "preemption", "sovereign immunity", "eleventh amendment", "states' rights"],
    },
    "iss-tax": {
        "name": "Tax Law",
        "keywords": ["tax", "irs", "internal revenue", "taxation"],
    },
    "iss-labor": {
        "name": "Labor Law",
        "keywords": ["labor", "nlrb", "collective bargaining", "union", "employment", "flsa", "wage"],
    },
    "iss-patent": {
        "name": "Patent Law",
        "keywords": ["patent", "inter partes review", "ptab"],
    },
    "iss-voting": {
        "name": "Voting Rights",
        "keywords": ["voting rights", "gerrymandering", "redistricting", "election", "voting"],
    },
    "iss-environmental": {
        "name": "Environmental Law",
        "keywords": ["environmental", "epa", "clean air", "clean water", "endangered species"],
    },
}


def _slugify_justice(name: str) -> str:
    """Convert 'Brett M. Kavanaugh' to 'j-kavanaugh'."""
    cleaned = re.sub(r'\b(Jr\.?|Sr\.?|II|III)\b', '', name)
    cleaned = re.sub(r'\b[A-Z]\.', '', cleaned)  # Middle initials
    cleaned = re.sub(r'\bChief\s+Justice\b|\bJustice\b', '', cleaned, flags=re.IGNORECASE)
    parts = [p for p in cleaned.strip().split() if p]
    if not parts:
        return "j-unknown"
    last = parts[-1].lower().strip('.,')
    return f"j-{last}"


def _parse_metadata(content: str) -> dict:
    """Extract bold-labeled fields from the top of the file."""
    meta = {}
    for match in re.finditer(r'\*\*([^*]+):\*\*\s*([^\n]+)', content):
        key = match.group(1).strip().lower().replace(' ', '_')
        value = match.group(2).strip()
        meta[key] = value
    return meta


def _parse_section(content: str, section_name: str) -> str:
    """Extract a ## section by name. Returns empty string if not found."""
    pattern = rf'##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##\s|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def _parse_votes(vote_section: str) -> list:
    """Parse per-justice vote lines from the Vote Breakdown section."""
    votes = []
    for line in vote_section.split('\n'):
        match = re.match(
            r'-\s*\*\*([^*]+)\*\*\s*[—\-]+\s*voted\s+(majority|minority)(?:\s*\(([^)]+)\))?',
            line,
        )
        if match:
            name = match.group(1).strip()
            side = match.group(2).strip()
            role = match.group(3).strip() if match.group(3) else None
            votes.append({
                "justice_name": name,
                "justice_id": _slugify_justice(name),
                "side": side,
                "role": role,
            })
    return votes


_NAME = r'([A-Z][A-Za-z\.\-]+(?:\s+[A-Z][A-Za-z\.\-]+){1,3})'


def _clean_author(name: str):
    """Trim trailing words and punctuation from a captured author name."""
    if not name:
        return None
    name = name.strip().rstrip(',.')
    # Drop trailing connector words that sometimes get captured
    tail = re.compile(r'\s+(the|wrote|held|delivered|authored|filed|issued|joined|and|,).*$', re.IGNORECASE)
    name = tail.sub('', name).strip().rstrip(',.')
    return name or None


def _extract_majority_author(decision_text: str):
    """Try several patterns to find the majority opinion author."""
    patterns = [
        # "opinion authored by (Chief) Justice X"
        rf'opinion\s+authored\s+by\s+(?:Chief\s+)?Justice\s+{_NAME}',
        # "opinion by (Chief) Justice X"
        rf'\bopinion\s+by\s+(?:Chief\s+)?Justice\s+{_NAME}',
        # "N-N opinion by (Chief) Justice X" / "N-N opinion authored by ..."
        rf'\d+[-–]\d+\s+(?:majority\s+)?(?:opinion|decision)\s+(?:authored\s+)?by\s+(?:Chief\s+)?Justice\s+{_NAME}',
        # "Justice X delivered the (majority) opinion"
        rf'(?:Chief\s+)?Justice\s+{_NAME}\s+delivered\s+the\s+(?:majority\s+)?opinion',
        # "Justice X authored/wrote the (N-N) (majority|unanimous) opinion"
        rf'(?:Chief\s+)?Justice\s+{_NAME}\s+(?:authored|wrote)\s+(?:the\s+)?(?:\d+[-–]\d+\s+)?(?:majority|unanimous)?\s*opinion',
        # "Justice X delivered (an|the) opinion for ..."
        rf'(?:Chief\s+)?Justice\s+{_NAME}\s+delivered\s+(?:an?|the)\s+opinion',
        # "Justice X delivered the N-N majority opinion"
        rf'(?:Chief\s+)?Justice\s+{_NAME}\s+delivered\s+the\s+\d+[-–]\d+\s+(?:majority\s+)?opinion',
        # "In a N-N opinion/decision (authored|delivered|written) by (Chief) Justice X"
        rf'In\s+an?\s+\d+[-–]\d+\s+(?:opinion|decision)\s+(?:authored|delivered|written)\s+by\s+(?:Chief\s+)?Justice\s+{_NAME}',
        # "written by (Chief) Justice X"
        rf'written\s+by\s+(?:Chief\s+)?Justice\s+{_NAME}',
        # "Writing for a (N-N) (majority|plurality|unanimous Court), Justice X"
        rf'Writing\s+for\s+(?:an?\s+)?(?:\d+[-–]\d+\s+)?(?:majority|plurality|unanimous\s+Court|the\s+Court)[^,\.]*,\s+(?:Chief\s+)?Justice\s+{_NAME}',
        # "Justice X authored/wrote an opinion for the ... plurality/majority"
        rf'(?:Chief\s+)?Justice\s+{_NAME}\s+(?:authored|wrote)\s+an?\s+(?:\d+[-–]\d+\s+)?(?:plurality|majority)?\s*opinion',
        # "Justice X announced the judgment"
        rf'(?:Chief\s+)?Justice\s+{_NAME}\s+announced\s+the\s+judgment',
        # "plurality opinion by (Chief) Justice X"
        rf'plurality\s+opinion\s+by\s+(?:Chief\s+)?Justice\s+{_NAME}',
    ]
    for p in patterns:
        m = re.search(p, decision_text)
        if m:
            return _clean_author(m.group(1))
    return None


def _extract_dissent_authors(decision_text: str) -> list:
    """Find dissent authors from decision text."""
    authors = []
    patterns = [
        r'(?:Chief\s+)?Justice\s+([A-Z][\w\s\.]+?)\s+(?:filed|wrote)\s+a\s+dissenting\s+opinion',
        r'(?:Chief\s+)?Justice\s+([A-Z][\w\s\.]+?)(?:,\s+joined\s+by[^,]*,)?\s+dissented',
    ]
    for p in patterns:
        for m in re.finditer(p, decision_text):
            name = m.group(1).strip().rstrip(',.')
            if name not in authors:
                authors.append(name)
    return authors


def _classify_issues(case_text: str) -> list:
    """Return list of issue IDs whose keywords appear in the case text."""
    text_lower = case_text.lower()
    matched = []
    for issue_id, data in ISSUE_KEYWORDS.items():
        if any(kw in text_lower for kw in data["keywords"]):
            matched.append(issue_id)
    return matched


def parse_case_file(filepath: str):
    """Parse a single SCOTUS markdown case file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if not h1_match:
        return None
    case_name = h1_match.group(1).strip()

    filename = Path(filepath).stem
    case_id = f"case-{filename}"

    meta = _parse_metadata(content)
    term = meta.get("term", "")
    docket = meta.get("docket_number", "")
    citation = meta.get("citation", "")
    petitioner = meta.get("petitioner", "")
    respondent = meta.get("respondent", "")

    question = _parse_section(content, "Question Presented")
    summary = _parse_section(content, "Summary")
    facts = _parse_section(content, "Facts of the Case")
    decision = _parse_section(content, "Decision")
    vote_section = _parse_section(content, "Vote Breakdown")

    votes = _parse_votes(vote_section)

    maj_count = sum(1 for v in votes if v["side"] == "majority")
    min_count = sum(1 for v in votes if v["side"] == "minority")
    vote_split = f"{maj_count}-{min_count}" if (maj_count + min_count) > 0 else "unknown"

    winning_match = re.search(r'Winning party:\s*([^\n]+)', vote_section)
    winning_party = winning_match.group(1).strip() if winning_match else ""

    majority_author_name = _extract_majority_author(decision)
    dissent_author_names = _extract_dissent_authors(decision)

    majority_author_id = _slugify_justice(majority_author_name) if majority_author_name else None
    dissent_author_ids = [_slugify_justice(n) for n in dissent_author_names]

    full_text = f"{case_name}\n{question}\n{summary}\n{facts}\n{decision}"
    issue_ids = _classify_issues(full_text)

    try:
        term_int = int(term)
    except (ValueError, TypeError):
        term_int = None

    return {
        "id": case_id,
        "name": case_name,
        "docket": docket,
        "citation": citation,
        "term": term_int,
        "term_str": term,
        "petitioner": petitioner,
        "respondent": respondent,
        "question": question,
        "summary": summary,
        "facts": facts,
        "decision": decision,
        "vote_split": vote_split,
        "winning_party": winning_party,
        "votes": votes,
        "majority_author_id": majority_author_id,
        "majority_author_name": majority_author_name,
        "dissent_author_ids": dissent_author_ids,
        "dissent_author_names": dissent_author_names,
        "issue_ids": issue_ids,
    }


def parse_all_cases(source_dir: str = SCOTUS_SOURCE_DIR) -> list:
    """Parse all case files in the source directory."""
    cases = []
    for filepath in sorted(Path(source_dir).glob("*.md")):
        parsed = parse_case_file(str(filepath))
        if parsed:
            cases.append(parsed)
    return cases


def derive_justices(cases: list) -> list:
    """Collect unique justices from vote records."""
    seen = {}
    for case in cases:
        for vote in case["votes"]:
            jid = vote["justice_id"]
            term = case["term"]
            if jid not in seen:
                seen[jid] = {
                    "id": jid,
                    "name": vote["justice_name"],
                    "first_term": term if term else 2018,
                    "last_term": term if term else 2023,
                }
            else:
                if term:
                    if seen[jid]["first_term"] is None or term < seen[jid]["first_term"]:
                        seen[jid]["first_term"] = term
                    if seen[jid]["last_term"] is None or term > seen[jid]["last_term"]:
                        seen[jid]["last_term"] = term
    return list(seen.values())


def derive_issues() -> list:
    """Return the fixed issue taxonomy."""
    return [
        {"id": issue_id, "name": data["name"], "category": "legal"}
        for issue_id, data in ISSUE_KEYWORDS.items()
    ]


def derive_citations(cases: list) -> list:
    """Find citations between cases by looking for case names in decision/facts text."""
    name_to_id = {c["name"].lower(): c["id"] for c in cases}
    citations = []
    seen = set()
    for case in cases:
        search_text = f"{case['decision']} {case['facts']}".lower()
        for other_name, other_id in name_to_id.items():
            if other_id == case["id"]:
                continue
            if " v. " in other_name and other_name in search_text:
                key = (case["id"], other_id)
                if key not in seen:
                    seen.add(key)
                    citations.append({"from_id": case["id"], "to_id": other_id})
    return citations


def build_documents(cases: list) -> list:
    """Build documents for vector indexing. 2 docs per case (overview + decision)."""
    docs = []
    for case in cases:
        author_id = case["majority_author_id"] or "j-unknown"

        overview_content = "\n\n".join(filter(None, [
            f"Question Presented: {case['question']}" if case["question"] else "",
            f"Summary: {case['summary']}" if case["summary"] else "",
            f"Facts: {case['facts']}" if case["facts"] else "",
        ]))
        if overview_content:
            docs.append({
                "id": f"{case['id']}-overview",
                "title": f"{case['name']}: Overview",
                "content": overview_content[:4000],
                "doc_type": "case_overview",
                "author_id": author_id,
                "project_id": case["id"],
                "dataset": "scotus",
                "created_at": f"{case['term'] or 2020}-06-15",
            })

        if case["decision"]:
            docs.append({
                "id": f"{case['id']}-decision",
                "title": f"{case['name']}: Decision",
                "content": case["decision"][:4000],
                "doc_type": "decision",
                "author_id": author_id,
                "project_id": case["id"],
                "dataset": "scotus",
                "created_at": f"{case['term'] or 2020}-06-15",
            })
    return docs


def generate_all() -> dict:
    """Parse the full SCOTUS corpus and return structured data."""
    cases = parse_all_cases()
    justices = derive_justices(cases)
    issues = derive_issues()
    citations = derive_citations(cases)
    documents = build_documents(cases)
    return {
        "justices": justices,
        "issues": issues,
        "cases": cases,
        "citations": citations,
        "documents": documents,
    }


if __name__ == "__main__":
    data = generate_all()
    print(f"Cases: {len(data['cases'])}")
    print(f"Justices: {len(data['justices'])}")
    print(f"Issues: {len(data['issues'])}")
    print(f"Citations: {len(data['citations'])}")
    print(f"Documents: {len(data['documents'])}")

    maj_ok = sum(1 for c in data['cases'] if c['majority_author_id'])
    total = len(data['cases'])
    print(f"\nMajority author extraction: {maj_ok}/{total} ({100*maj_ok//max(total,1)}%)")
    dis_ok = sum(1 for c in data['cases'] if c['dissent_author_ids'])
    print(f"Dissent author extraction: {dis_ok}/{total} cases had at least one dissent author")

    if data['cases']:
        c = data['cases'][0]
        print(f"\nSample case: {c['name']}")
        print(f"  ID: {c['id']}")
        print(f"  Term: {c['term']}")
        print(f"  Docket: {c['docket']}")
        print(f"  Vote split: {c['vote_split']}")
        print(f"  Winning party: {c['winning_party']}")
        print(f"  Majority author: {c['majority_author_name']} ({c['majority_author_id']})")
        print(f"  Dissent authors: {c['dissent_author_names']}")
        print(f"  Issues: {c['issue_ids']}")
        print(f"  Votes: {len(c['votes'])}")
        print(f"\nJustices found: {[j['name'] for j in data['justices']]}")
