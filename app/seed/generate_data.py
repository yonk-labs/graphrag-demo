"""
Generates a fictional org dataset for the GraphRAG demo.
Outputs a JSON structure with people, teams, projects, services,
technologies, relationships, and documents.
"""

import json
import random
from datetime import datetime, timedelta

from seed.templates import ALL_TEMPLATES

random.seed(42)  # Deterministic output


def _random_date(start_year=2025, end_year=2026) -> str:
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 6, 30)
    delta = end - start
    offset = random.randint(0, delta.days)
    return (start + timedelta(days=offset)).strftime("%Y-%m-%d")


# --- Org definition ---

TEAMS = [
    {"id": "team-eng", "name": "Engineering", "department": "Engineering"},
    {"id": "team-data", "name": "Data", "department": "Engineering"},
    {"id": "team-product", "name": "Product", "department": "Product"},
    {"id": "team-platform", "name": "Platform", "department": "Engineering"},
]

PEOPLE = [
    {"id": "p-alice", "name": "Alice Chen", "title": "Staff Engineer", "email": "alice@acmelabs.io", "team_id": "team-eng"},
    {"id": "p-bob", "name": "Bob Martinez", "title": "Senior Engineer", "email": "bob@acmelabs.io", "team_id": "team-eng"},
    {"id": "p-carol", "name": "Carol Washington", "title": "Engineering Manager", "email": "carol@acmelabs.io", "team_id": "team-eng"},
    {"id": "p-david", "name": "David Kim", "title": "Data Engineer", "email": "david@acmelabs.io", "team_id": "team-data"},
    {"id": "p-elena", "name": "Elena Petrov", "title": "Senior Data Engineer", "email": "elena@acmelabs.io", "team_id": "team-data"},
    {"id": "p-frank", "name": "Frank Okafor", "title": "Data Team Lead", "email": "frank@acmelabs.io", "team_id": "team-data"},
    {"id": "p-grace", "name": "Grace Liu", "title": "Product Manager", "email": "grace@acmelabs.io", "team_id": "team-product"},
    {"id": "p-hassan", "name": "Hassan Ali", "title": "Senior PM", "email": "hassan@acmelabs.io", "team_id": "team-product"},
    {"id": "p-iris", "name": "Iris Nakamura", "title": "UX Designer", "email": "iris@acmelabs.io", "team_id": "team-product"},
    {"id": "p-james", "name": "James O'Brien", "title": "Platform Engineer", "email": "james@acmelabs.io", "team_id": "team-platform"},
    {"id": "p-kate", "name": "Kate Johansson", "title": "Senior Platform Engineer", "email": "kate@acmelabs.io", "team_id": "team-platform"},
    {"id": "p-leo", "name": "Leo Fernandez", "title": "Platform Team Lead", "email": "leo@acmelabs.io", "team_id": "team-platform"},
    {"id": "p-maya", "name": "Maya Singh", "title": "Junior Engineer", "email": "maya@acmelabs.io", "team_id": "team-eng"},
    {"id": "p-nate", "name": "Nate Cooper", "title": "DevOps Engineer", "email": "nate@acmelabs.io", "team_id": "team-platform"},
    {"id": "p-olivia", "name": "Olivia Reeves", "title": "Data Scientist", "email": "olivia@acmelabs.io", "team_id": "team-data"},
]

PROJECTS = [
    {"id": "proj-billing", "name": "Billing Migration", "description": "Migrate billing system to new payment processor", "status": "active"},
    {"id": "proj-search", "name": "Search Redesign", "description": "Rebuild the search infrastructure for better relevance", "status": "active"},
    {"id": "proj-auth", "name": "Auth Overhaul", "description": "Replace legacy auth with OAuth2/OIDC", "status": "active"},
    {"id": "proj-dashboard", "name": "Analytics Dashboard", "description": "Build real-time analytics dashboard for customers", "status": "active"},
    {"id": "proj-ml-pipeline", "name": "ML Pipeline", "description": "Production ML feature pipeline for recommendation engine", "status": "active"},
    {"id": "proj-mobile", "name": "Mobile App v2", "description": "Major mobile app rewrite with offline support", "status": "planning"},
    {"id": "proj-infra", "name": "Infrastructure Modernization", "description": "Migrate from VMs to Kubernetes", "status": "active"},
    {"id": "proj-data-lake", "name": "Data Lake Consolidation", "description": "Unify data sources into single lakehouse", "status": "active"},
]

SERVICES = [
    {"id": "svc-auth", "name": "Auth Service", "description": "handles authentication and authorization", "tier": "critical"},
    {"id": "svc-payment", "name": "Payment Service", "description": "processes payments and manages subscriptions", "tier": "critical"},
    {"id": "svc-search", "name": "Search API", "description": "full-text and semantic search across the platform", "tier": "standard"},
    {"id": "svc-notify", "name": "Notification Service", "description": "sends emails, push notifications, and webhooks", "tier": "standard"},
    {"id": "svc-analytics", "name": "Analytics Ingestion", "description": "collects and processes analytics events", "tier": "internal"},
]

TECHNOLOGIES = [
    {"id": "tech-postgres", "name": "PostgreSQL", "category": "database"},
    {"id": "tech-redis", "name": "Redis", "category": "cache"},
    {"id": "tech-kafka", "name": "Kafka", "category": "messaging"},
    {"id": "tech-k8s", "name": "Kubernetes", "category": "orchestration"},
    {"id": "tech-python", "name": "Python", "category": "language"},
    {"id": "tech-typescript", "name": "TypeScript", "category": "language"},
    {"id": "tech-spark", "name": "Apache Spark", "category": "processing"},
    {"id": "tech-elasticsearch", "name": "Elasticsearch", "category": "search"},
    {"id": "tech-graphql", "name": "GraphQL", "category": "api"},
    {"id": "tech-terraform", "name": "Terraform", "category": "infrastructure"},
]

# --- Relationships ---

WORKS_ON = [
    ("p-alice", "proj-billing", "tech lead"),
    ("p-alice", "proj-auth", "contributor"),
    ("p-bob", "proj-billing", "engineer"),
    ("p-bob", "proj-search", "engineer"),
    ("p-carol", "proj-billing", "manager"),
    ("p-carol", "proj-auth", "manager"),
    ("p-david", "proj-data-lake", "engineer"),
    ("p-david", "proj-ml-pipeline", "engineer"),
    ("p-elena", "proj-ml-pipeline", "tech lead"),
    ("p-elena", "proj-data-lake", "contributor"),
    ("p-frank", "proj-data-lake", "lead"),
    ("p-frank", "proj-dashboard", "contributor"),
    ("p-grace", "proj-billing", "pm"),
    ("p-grace", "proj-mobile", "pm"),
    ("p-hassan", "proj-search", "pm"),
    ("p-hassan", "proj-dashboard", "pm"),
    ("p-iris", "proj-mobile", "designer"),
    ("p-iris", "proj-dashboard", "designer"),
    ("p-james", "proj-infra", "engineer"),
    ("p-james", "proj-auth", "engineer"),
    ("p-kate", "proj-infra", "tech lead"),
    ("p-kate", "proj-search", "contributor"),
    ("p-leo", "proj-infra", "lead"),
    ("p-leo", "proj-billing", "contributor"),
    ("p-maya", "proj-search", "engineer"),
    ("p-maya", "proj-mobile", "engineer"),
    ("p-nate", "proj-infra", "engineer"),
    ("p-nate", "proj-ml-pipeline", "contributor"),
    ("p-olivia", "proj-ml-pipeline", "data scientist"),
    ("p-olivia", "proj-dashboard", "contributor"),
]

REPORTS_TO = [
    ("p-alice", "p-carol"),
    ("p-bob", "p-carol"),
    ("p-maya", "p-carol"),
    ("p-david", "p-frank"),
    ("p-elena", "p-frank"),
    ("p-olivia", "p-frank"),
    ("p-iris", "p-hassan"),
    ("p-grace", "p-hassan"),
    ("p-james", "p-leo"),
    ("p-kate", "p-leo"),
    ("p-nate", "p-leo"),
]

OWNS = [
    ("team-eng", "svc-payment"),
    ("team-eng", "svc-search"),
    ("team-platform", "svc-auth"),
    ("team-platform", "svc-notify"),
    ("team-data", "svc-analytics"),
]

DEPENDS_ON = [
    ("proj-billing", "svc-payment", "core"),
    ("proj-billing", "svc-auth", "auth"),
    ("proj-search", "svc-search", "core"),
    ("proj-search", "svc-auth", "auth"),
    ("proj-dashboard", "svc-analytics", "data"),
    ("proj-ml-pipeline", "svc-analytics", "data"),
    ("proj-auth", "svc-auth", "core"),
    ("proj-mobile", "svc-auth", "auth"),
    ("proj-mobile", "svc-notify", "notifications"),
    ("svc-payment", "svc-auth", "auth"),
    ("svc-payment", "svc-notify", "notifications"),
    ("svc-search", "svc-auth", "auth"),
    ("svc-analytics", "svc-auth", "auth"),
]

KNOWS_ABOUT = [
    ("p-alice", "tech-python", "expert"),
    ("p-alice", "tech-postgres", "expert"),
    ("p-alice", "tech-kafka", "intermediate"),
    ("p-bob", "tech-typescript", "expert"),
    ("p-bob", "tech-graphql", "expert"),
    ("p-bob", "tech-postgres", "intermediate"),
    ("p-carol", "tech-python", "intermediate"),
    ("p-david", "tech-spark", "expert"),
    ("p-david", "tech-python", "expert"),
    ("p-david", "tech-kafka", "intermediate"),
    ("p-elena", "tech-python", "expert"),
    ("p-elena", "tech-spark", "expert"),
    ("p-elena", "tech-postgres", "expert"),
    ("p-frank", "tech-postgres", "expert"),
    ("p-frank", "tech-kafka", "expert"),
    ("p-frank", "tech-spark", "intermediate"),
    ("p-james", "tech-k8s", "expert"),
    ("p-james", "tech-terraform", "expert"),
    ("p-kate", "tech-k8s", "expert"),
    ("p-kate", "tech-postgres", "intermediate"),
    ("p-kate", "tech-redis", "expert"),
    ("p-leo", "tech-terraform", "expert"),
    ("p-leo", "tech-k8s", "expert"),
    ("p-maya", "tech-typescript", "intermediate"),
    ("p-maya", "tech-elasticsearch", "beginner"),
    ("p-nate", "tech-terraform", "expert"),
    ("p-nate", "tech-k8s", "intermediate"),
    ("p-olivia", "tech-python", "expert"),
    ("p-olivia", "tech-spark", "intermediate"),
]


def _people_by_id():
    return {p["id"]: p for p in PEOPLE}


def _projects_by_id():
    return {p["id"]: p for p in PROJECTS}


def _services_by_id():
    return {s["id"]: s for s in SERVICES}


def _teams_by_id():
    return {t["id"]: t for t in TEAMS}


def _techs_by_id():
    return {t["id"]: t for t in TECHNOLOGIES}


def _pick_others(exclude_id: str, team_id: str | None = None, count: int = 3) -> list[dict]:
    """Pick random people, optionally biased toward the same team."""
    pool = [p for p in PEOPLE if p["id"] != exclude_id]
    if team_id:
        same_team = [p for p in pool if p["team_id"] == team_id]
        other_team = [p for p in pool if p["team_id"] != team_id]
        # Bias: 70% same team, 30% other
        result = []
        for _ in range(count):
            if same_team and random.random() < 0.7:
                result.append(random.choice(same_team))
            elif other_team:
                result.append(random.choice(other_team))
            elif same_team:
                result.append(random.choice(same_team))
        return result
    return random.sample(pool, min(count, len(pool)))


# Subject types per template index (matches order in templates.py)
TEMPLATE_SUBJECTS = {
    "meeting_note": ["project", "team", "cross_team", "one_on_one", "project"],
    "architecture_doc": ["service", "project", "project"],
    "incident_report": ["service", "service"],
    "decision_record": ["project", "service", "project"],
}


def generate_documents() -> list[dict]:
    """Generate ~160 documents using templates and real entity references.

    Each template has a 'subject type' that drives how author/project/service are
    picked so graph relationships correlate with document content. This lets graph
    traversal surface docs via ownership/membership chains even without a semantic
    match, which is the whole point of the demo.
    """
    teams = _teams_by_id()

    docs = []
    doc_id = 0

    for doc_type, templates in ALL_TEMPLATES.items():
        iterations = 16 if doc_type == "meeting_note" else 10
        for template_idx, (template_title, template_content) in enumerate(templates):
            subject_type = TEMPLATE_SUBJECTS[doc_type][template_idx]
            for _ in range(iterations):
                person2_candidate_id = None
                team_subject = None

                if subject_type == "service":
                    svc_subject = random.choice(SERVICES)
                    svc = svc_subject
                    owning_team_id = next((t for t, s in OWNS if s == svc_subject["id"]), None)
                    if owning_team_id and random.random() < 0.7:
                        candidates = [p for p in PEOPLE if p["team_id"] == owning_team_id]
                    else:
                        dep_projs = [s for s, t, _ in DEPENDS_ON if t == svc_subject["id"] and s.startswith("proj-")]
                        if dep_projs:
                            dep_proj = random.choice(dep_projs)
                            worker_ids = {p for p, pr, _ in WORKS_ON if pr == dep_proj}
                            candidates = [p for p in PEOPLE if p["id"] in worker_ids]
                        else:
                            candidates = [p for p in PEOPLE if p["team_id"] == owning_team_id] if owning_team_id else list(PEOPLE)
                    author = random.choice(candidates) if candidates else random.choice(PEOPLE)
                    dep_projs = [s for s, t, _ in DEPENDS_ON if t == svc_subject["id"] and s.startswith("proj-")]
                    proj_id = random.choice(dep_projs) if dep_projs else None
                    proj = next((p for p in PROJECTS if p["id"] == proj_id), None) or random.choice(PROJECTS)
                    svc2_choices = [s for s in SERVICES if s["id"] != svc["id"]]
                    svc2 = random.choice(svc2_choices)
                    svc3_choices = [s for s in SERVICES if s["id"] not in (svc["id"], svc2["id"])]
                    svc3 = random.choice(svc3_choices) if svc3_choices else svc2

                elif subject_type == "project":
                    proj_subject = random.choice(PROJECTS)
                    proj = proj_subject
                    worker_ids = {p for p, pr, _ in WORKS_ON if pr == proj_subject["id"]}
                    candidates = [p for p in PEOPLE if p["id"] in worker_ids]
                    author = random.choice(candidates) if candidates else random.choice(PEOPLE)
                    dep_svcs = [t for s, t, _ in DEPENDS_ON if s == proj_subject["id"]]
                    svc = next((s for s in SERVICES if s["id"] in dep_svcs), None) or random.choice(SERVICES)
                    svc2_choices = [s for s in SERVICES if s["id"] != svc["id"]]
                    svc2 = random.choice(svc2_choices)
                    svc3_choices = [s for s in SERVICES if s["id"] not in (svc["id"], svc2["id"])]
                    svc3 = random.choice(svc3_choices) if svc3_choices else svc2

                elif subject_type == "team":
                    team_subject = random.choice(TEAMS)
                    candidates = [p for p in PEOPLE if p["team_id"] == team_subject["id"]]
                    author = random.choice(candidates) if candidates else random.choice(PEOPLE)
                    team_member_ids = {p["id"] for p in candidates}
                    team_proj_ids = list({pr for p, pr, _ in WORKS_ON if p in team_member_ids})
                    if team_proj_ids:
                        chosen = random.choice(team_proj_ids)
                        proj = next((p for p in PROJECTS if p["id"] == chosen), random.choice(PROJECTS))
                    else:
                        proj = random.choice(PROJECTS)
                    svc = random.choice(SERVICES)
                    svc2_choices = [s for s in SERVICES if s["id"] != svc["id"]]
                    svc2 = random.choice(svc2_choices)
                    svc3_choices = [s for s in SERVICES if s["id"] not in (svc["id"], svc2["id"])]
                    svc3 = random.choice(svc3_choices) if svc3_choices else svc2

                elif subject_type == "cross_team":
                    proj = random.choice(PROJECTS)
                    worker_ids = {p for p, pr, _ in WORKS_ON if pr == proj["id"]}
                    candidates = [p for p in PEOPLE if p["id"] in worker_ids]
                    author = random.choice(candidates) if candidates else random.choice(PEOPLE)
                    svc = random.choice(SERVICES)
                    svc2_choices = [s for s in SERVICES if s["id"] != svc["id"]]
                    svc2 = random.choice(svc2_choices)
                    svc3_choices = [s for s in SERVICES if s["id"] not in (svc["id"], svc2["id"])]
                    svc3 = random.choice(svc3_choices) if svc3_choices else svc2

                elif subject_type == "one_on_one":
                    managers = list({m for _, m in REPORTS_TO})
                    manager_id = random.choice(managers)
                    author = next(p for p in PEOPLE if p["id"] == manager_id)
                    reports = [p for p, m in REPORTS_TO if m == manager_id]
                    person2_candidate_id = random.choice(reports) if reports else None
                    if person2_candidate_id:
                        report_projs = [pr for p, pr, _ in WORKS_ON if p == person2_candidate_id]
                        if report_projs:
                            chosen = random.choice(report_projs)
                            proj = next((p for p in PROJECTS if p["id"] == chosen), random.choice(PROJECTS))
                        else:
                            proj = random.choice(PROJECTS)
                    else:
                        proj = random.choice(PROJECTS)
                    svc = random.choice(SERVICES)
                    svc2_choices = [s for s in SERVICES if s["id"] != svc["id"]]
                    svc2 = random.choice(svc2_choices)
                    svc3_choices = [s for s in SERVICES if s["id"] not in (svc["id"], svc2["id"])]
                    svc3 = random.choice(svc3_choices) if svc3_choices else svc2

                else:
                    author = random.choice(PEOPLE)
                    proj = random.choice(PROJECTS)
                    svc = random.choice(SERVICES)
                    svc2_choices = [s for s in SERVICES if s["id"] != svc["id"]]
                    svc2 = random.choice(svc2_choices)
                    svc3_choices = [s for s in SERVICES if s["id"] not in (svc["id"], svc2["id"])]
                    svc3 = random.choice(svc3_choices) if svc3_choices else svc2

                others = _pick_others(author["id"], author["team_id"], count=4)
                team = team_subject if subject_type == "team" and team_subject else teams[author["team_id"]]
                other_teams = [t for t in TEAMS if t["id"] != author["team_id"]]
                team2 = random.choice(other_teams)
                proj2_choices = [p for p in PROJECTS if p["id"] != proj["id"]]
                proj2 = random.choice(proj2_choices)
                tech_list = random.sample(TECHNOLOGIES, min(3, len(TECHNOLOGIES)))

                # For 1:1, ensure person2 is the direct report (drives graph linkage)
                if subject_type == "one_on_one" and person2_candidate_id:
                    report_person = next((p for p in PEOPLE if p["id"] == person2_candidate_id), None)
                    if report_person:
                        others = [report_person] + [o for o in others if o["id"] != report_person["id"]][:3]

                replacements = {
                    "author": author["name"],
                    "person2": others[0]["name"] if len(others) > 0 else "a colleague",
                    "person3": others[1]["name"] if len(others) > 1 else "a teammate",
                    "person4": others[2]["name"] if len(others) > 2 else "someone",
                    "team": team["name"],
                    "team2": team2["name"],
                    "project": proj["name"],
                    "project2": proj2["name"],
                    "service": svc["name"],
                    "service_desc": svc["description"],
                    "service2": svc2["name"],
                    "service3": svc3["name"],
                    "technology": tech_list[0]["name"],
                    "technology2": tech_list[1]["name"] if len(tech_list) > 1 else "Redis",
                    "technology3": tech_list[2]["name"] if len(tech_list) > 2 else "Kafka",
                    "date": _random_date(),
                }

                title = template_title.format(**replacements)
                content = template_content.format(**replacements)

                docs.append({
                    "id": f"doc-{doc_id:04d}",
                    "title": title,
                    "content": content,
                    "doc_type": doc_type,
                    "author_id": author["id"],
                    "project_id": proj["id"],
                    "dataset": "acme",
                    "created_at": _random_date(),
                })
                doc_id += 1

    return docs


def generate_all() -> dict:
    """Generate the complete dataset."""
    documents = generate_documents()
    return {
        "teams": TEAMS,
        "people": PEOPLE,
        "projects": PROJECTS,
        "services": SERVICES,
        "technologies": TECHNOLOGIES,
        "relationships": {
            "works_on": [{"person_id": p, "project_id": pr, "role": r} for p, pr, r in WORKS_ON],
            "reports_to": [{"person_id": p, "manager_id": m} for p, m in REPORTS_TO],
            "owns": [{"team_id": t, "service_id": s} for t, s in OWNS],
            "depends_on": [{"source_id": s, "target_id": t, "dependency_type": d} for s, t, d in DEPENDS_ON],
            "knows_about": [{"person_id": p, "tech_id": t, "proficiency": pr} for p, t, pr in KNOWS_ABOUT],
        },
        "documents": documents,
    }


if __name__ == "__main__":
    data = generate_all()
    print(json.dumps(data, indent=2))
    print(f"\nGenerated: {len(data['documents'])} documents, "
          f"{len(data['people'])} people, {len(data['projects'])} projects, "
          f"{len(data['services'])} services")
