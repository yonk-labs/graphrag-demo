"""
Document content templates for the fictional org Acme Labs.
Each template uses {placeholders} that get filled with real entity names
from the graph so documents reference actual people, projects, and services.
"""

MEETING_NOTE_TEMPLATES = [
    (
        "Weekly sync: {project} status update",
        "{author} led the weekly {project} sync. Key updates: the {service} "
        "integration is on track. {person2} raised a concern about latency in "
        "the {service2} dependency. We agreed to run load tests next week. "
        "{person3} will handle the monitoring dashboard setup. Next sync is "
        "scheduled for {date}."
    ),
    (
        "{team} planning: Q2 priorities",
        "The {team} team met to discuss Q2 priorities. {author} proposed "
        "focusing on {project} stabilization before adding new features. "
        "{person2} suggested we also invest in {technology} adoption. "
        "The team voted to prioritize reliability. {person3} will draft "
        "the updated roadmap by end of week."
    ),
    (
        "Cross-team sync: {project} and {project2} alignment",
        "{author} organized a cross-team sync between {team} and {team2} "
        "to discuss shared dependencies. The {service} is used by both "
        "{project} and {project2}. {person2} from {team2} proposed a "
        "shared API contract. {person3} will own the contract definition. "
        "Follow-up scheduled for {date}."
    ),
    (
        "1:1 notes: {author} and {person2}",
        "Discussed {person2}'s progress on {project}. They are making good "
        "headway on the {technology} migration. Blocker: waiting on {person3} "
        "to finish the {service} API changes. {person2} mentioned interest in "
        "learning {technology2}. Will connect them with {person4} who has "
        "expertise there."
    ),
    (
        "Sprint retro: {project}",
        "Sprint retro for {project}. What went well: {person2} shipped the "
        "{service} caching layer ahead of schedule. What could improve: "
        "deployments to staging are still manual. {author} will set up "
        "automated deploys. {person3} flagged that test coverage for the "
        "{technology} components is below 60%."
    ),
]

ARCHITECTURE_DOC_TEMPLATES = [
    (
        "{service} architecture overview",
        "The {service} is a core component of the Acme Labs platform, owned "
        "by the {team} team. It provides {service_desc}.\n\n"
        "Key dependencies: {service2}, {service3}.\n\n"
        "Technology stack: {technology}, {technology2}.\n\n"
        "The service handles approximately 50k requests per minute in "
        "production. {author} designed the current architecture during the "
        "Q3 rewrite. Primary maintainers: {person2}, {person3}."
    ),
    (
        "{project} technical design",
        "This document describes the technical design for {project}.\n\n"
        "Goals: improve {service} performance by 3x while maintaining "
        "backwards compatibility.\n\n"
        "Approach: introduce a caching layer using {technology} between "
        "the API gateway and {service2}. {author} will implement the cache "
        "invalidation strategy. {person2} will update the client SDKs.\n\n"
        "Risks: cache staleness could cause data inconsistency. Mitigation: "
        "TTL-based expiry with event-driven invalidation from {service3}."
    ),
    (
        "Data pipeline: {project} ingestion flow",
        "The data ingestion pipeline for {project} processes events from "
        "{service} and {service2}. Designed by {author}, maintained by "
        "{person2}.\n\n"
        "Flow: events land in the message queue, are transformed by the "
        "{technology} workers, validated against the schema registry, and "
        "written to the {technology2} data store.\n\n"
        "Current throughput: 10k events/sec. Scaling plan: partition by "
        "tenant ID. {person3} is researching {technology3} as an alternative "
        "processing engine."
    ),
]

INCIDENT_REPORT_TEMPLATES = [
    (
        "Incident: {service} outage on {date}",
        "Severity: P1\nDuration: 47 minutes\nImpact: all {project} users "
        "affected\n\n"
        "Root cause: a misconfigured deployment of {service} caused a "
        "cascading failure in {service2}. The {technology} connection pool "
        "was exhausted, which blocked all downstream requests.\n\n"
        "Detection: {person2} noticed elevated error rates in the monitoring "
        "dashboard at 14:23 UTC. {author} was paged and confirmed the issue.\n\n"
        "Resolution: {person3} rolled back the deployment. {author} applied "
        "a hotfix to the connection pool configuration.\n\n"
        "Action items: add connection pool health checks, implement circuit "
        "breaker between {service} and {service2}."
    ),
    (
        "Incident: {service} degraded performance",
        "Severity: P2\nDuration: 2 hours\nImpact: {project} experienced "
        "3x latency increase\n\n"
        "Root cause: {person2}'s query optimization for {project} introduced "
        "a full table scan on the {technology} index. The {service} CPU usage "
        "spiked to 95%.\n\n"
        "Detection: automated alerting triggered. {author} investigated.\n\n"
        "Resolution: reverted the query change. {person3} from {team} helped "
        "design a proper index strategy.\n\n"
        "Action items: add query plan review to PR checklist for {service} "
        "changes."
    ),
]

DECISION_RECORD_TEMPLATES = [
    (
        "Decision: migrate {project} to {technology}",
        "Status: Approved\nDecision maker: {author}\nDate: {date}\n\n"
        "Context: the current {technology2} stack for {project} is reaching "
        "scaling limits. {person2} benchmarked alternatives and {technology} "
        "showed 4x throughput improvement.\n\n"
        "Decision: migrate {project} to {technology} over Q2. {person3} will "
        "lead the migration. The {team} team will provide support.\n\n"
        "Tradeoffs: higher operational complexity, team needs to learn "
        "{technology}. Mitigated by: {person4} already has experience, "
        "will run internal training sessions."
    ),
    (
        "Decision: {service} ownership transfer to {team}",
        "Status: Approved\nDecision maker: {author}\nDate: {date}\n\n"
        "Context: {service} was originally built by {team2} but is now "
        "primarily used by {project}, which is owned by {team}. {person2} "
        "has been the de facto maintainer despite being on {team2}.\n\n"
        "Decision: transfer {service} ownership to {team}. {person3} will "
        "be the new primary maintainer. {person2} will provide a 2-week "
        "knowledge transfer.\n\n"
        "Tradeoffs: {team} takes on additional operational load. "
        "Mitigated by: {person2} remains available for escalations."
    ),
    (
        "Decision: adopt {technology} for billing migration",
        "Status: Approved\nDecision maker: {author}\nDate: {date}\n\n"
        "Context: the billing migration for {project} needs a reliable "
        "data synchronization layer. {person2} evaluated {technology} and "
        "{technology2}. {technology} was selected based on its support for "
        "exactly-once delivery.\n\n"
        "Decision: use {technology} for the billing data sync. {person3} "
        "will implement the producer side. {person4} will handle the "
        "consumer and reconciliation logic.\n\n"
        "The {team} team approved this at the architecture review on {date}."
    ),
]

ALL_TEMPLATES = {
    "meeting_note": MEETING_NOTE_TEMPLATES,
    "architecture_doc": ARCHITECTURE_DOC_TEMPLATES,
    "incident_report": INCIDENT_REPORT_TEMPLATES,
    "decision_record": DECISION_RECORD_TEMPLATES,
}
