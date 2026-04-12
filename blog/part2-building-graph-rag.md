# Building a Graph-Aware RAG Pipeline

We ended Part 1 with vector search confidently returning documents that were technically relevant and practically useless. The model was happy. The user was not. Now we fix it.

Here's the deal. Vector search alone is like asking a librarian who's read every book but never met another human. It knows what words mean next to each other, but it doesn't know that Sarah is on the payments team, that the payments team owns the auth service, and that the auth service is the reason your question even exists. That's structural knowledge. And you don't get structural knowledge from cosine similarity, no matter how many dimensions you throw at it.

So in this post we're going to build three retrieval strategies on top of the same Postgres database: one using pgvector only, one using Apache AGE only, and one that combines them into something that actually behaves like a colleague who knows the org. I've been building data pipelines for 20-plus years, and I'll tell you up front: this combined strategy isn't some genius new algorithm I invented in the shower. It's plumbing. Good plumbing. But still plumbing.

## The data model (the boring part that matters most)

Before any retrieval code, you need a graph. Apache AGE lets us declare nodes and edges as first-class citizens inside Postgres. Here's the whole schema, and yes, it's this short:

```sql
SELECT ag_catalog.create_graph('org_graph');

SELECT ag_catalog.create_vlabel('org_graph', 'Person');
SELECT ag_catalog.create_vlabel('org_graph', 'Team');
SELECT ag_catalog.create_vlabel('org_graph', 'Project');
SELECT ag_catalog.create_vlabel('org_graph', 'Service');
SELECT ag_catalog.create_vlabel('org_graph', 'Technology');

SELECT ag_catalog.create_elabel('org_graph', 'WORKS_ON');
SELECT ag_catalog.create_elabel('org_graph', 'MEMBER_OF');
SELECT ag_catalog.create_elabel('org_graph', 'DEPENDS_ON');
SELECT ag_catalog.create_elabel('org_graph', 'OWNS');
SELECT ag_catalog.create_elabel('org_graph', 'KNOWS_ABOUT');
SELECT ag_catalog.create_elabel('org_graph', 'REPORTS_TO');
SELECT ag_catalog.create_elabel('org_graph', 'AUTHORED');
```

Five node types, seven edge types. That's it. People work on projects, belong to teams, know about technologies. Projects depend on services. People report to other people. And people author documents. If you can draw it on a napkin at a bar, you can model it in AGE.

Now the bridge, which is the part most GraphRAG tutorials hand-wave past. The vector side lives in a normal Postgres table:

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN (
        'meeting_note', 'architecture_doc', 'incident_report', 'decision_record'
    )),
    author_id TEXT NOT NULL,
    project_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    embedding vector(384)
);
```

Notice `author_id` and `project_id`. Those are the glue. They're plain text columns in a relational table, but the values match the `id` property on Person and Project nodes over in the graph. No foreign keys. No triggers. Just a naming convention and a commitment to keep both sides in sync at write time. Think of it like the address on an envelope: the post office and the house don't share a schema, but if the address matches, the letter arrives.

Why no foreign key? Because AGE nodes aren't normal rows, and forcing referential integrity across the two worlds is the kind of elegant idea that eats your weekends. Been there. Bought the t-shirt. Still have the therapy bills.

## Strategy 1: Vector-only, the baseline we already know

You've seen this a hundred times, so I'm not going to linger. Embed the question, run a nearest-neighbor search, return the top K:

```python
with timed_stage(timing, "embedding"):
    query_embedding = self.embedding_provider.embed(question)

with timed_stage(timing, "vector_search"):
    cur.execute(
        """
        SELECT title, content, doc_type,
               1 - (embedding <=> %s::vector) AS similarity,
               author_id, project_id
        FROM documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (str(query_embedding), str(query_embedding), top_k),
    )
```

The `<=>` operator is pgvector's cosine distance. HNSW index does the heavy lifting. It's fast, it's standard, it's the starting line. This is the thing every RAG tutorial on the internet teaches, and for questions like "what did we decide about the billing migration" it actually works great. For questions like "who should I talk to about the payment service," it hands you three nicely-ranked architecture docs and zero humans. That's the problem.

## Strategy 2: Graph-only, or how to get nothing when nothing matches

Graph retrieval is a different animal. Instead of embedding the question, we try to find named entities in it, then traverse out from those entities to find related documents. Step one is loading what we know:

```python
for label, key in [
    ("Person", "people"),
    ("Project", "projects"),
    ("Service", "services"),
    ("Team", "teams"),
    ("Technology", "technologies"),
]:
    cur.execute(
        f"SELECT * FROM cypher('org_graph', $$ MATCH (n:{label}) RETURN n.id, n.name $$) "
        f"AS (id agtype, name agtype);"
    )
```

That `cypher(...)` call is AGE's party trick. You write real Cypher inside a SQL query, and AGE coerces the result into Postgres rows through that `agtype` cast. It's weird the first time you see it, then you get used to it, then you start wishing every database did this.

Entity extraction itself is embarrassingly simple. Lowercase the question, check if any known name is a substring. No fancy NER, no LLM call, no third model. If someone asks about "Sarah" and we have a Sarah in the graph, we match her:

```python
for category, label in label_map.items():
    for name, entity_id in known_entities[category].items():
        if name in q_lower:
            matches.append((label, entity_id))
```

Is this the state of the art? No. Could you swap in a proper extractor? Absolutely. But for the demo it does the job, and the point here is to show the pattern, not to win a Kaggle competition. (If you're building this for production, please use something better than `in`. I'm begging you.)

Once we have matches, we traverse. One hop, then two:

```python
cur.execute(
    f"SELECT * FROM cypher('org_graph', $$ "
    f"MATCH (n:{label} {{id: '{entity_id}'}})-[r]->(m) "
    f"RETURN labels(m), m.id, m.name, type(r) "
    f"$$) AS (labels agtype, id agtype, name agtype, rel_type agtype);"
)
```

Then we collect every Person and Project ID we touched, and we ask the documents table: give me everything authored by these people or belonging to these projects. That's the join point where the graph world hands its results back to the relational world.

The catch? If the question doesn't mention any known entity, graph retrieval returns an empty list. Zero results. A wall. This is a feature, not a bug, because it tells you honestly when it can't help. But it's also why graph-only is a lousy default strategy. Half your user questions are going to be phrased in ways that don't contain a single proper noun, and you can't serve those with a traversal. Which brings us to the star of the show.

## Strategy 3: Graph plus vector, the combined approach

Combined retrieval runs in three stages, and each one does what it's good at:

1. **Seed.** Vector search finds semantically relevant documents. No entity matching needed, so even vague questions get a foothold.
2. **Expand.** For each seed result, we look up its author and project in the graph, then traverse one or two hops to find colleagues on the same team and projects sharing dependencies.
3. **Rerank.** We merge the vector results and the graph-expanded results, deduplicate by title, and produce a weighted score that respects both signals.

Stage one is just the vector retrieval we already built, called verbatim. The interesting code is in stage two. For each seed document, we pull its `author_id` and `project_id`, then ask the graph two questions:

```python
cur.execute(
    "SELECT * FROM cypher('org_graph', $$ "
    f"MATCH (p:Person {{id: '{author_id}'}})-[:MEMBER_OF]->(t:Team)<-[:MEMBER_OF]-(colleague:Person) "
    "WHERE colleague <> p "
    "RETURN colleague.id "
    "$$) AS (id agtype);"
)
```

Question one: who are this author's teammates? Question two (if the seed doc has a project):

```python
cur.execute(
    "SELECT * FROM cypher('org_graph', $$ "
    f"MATCH (p:Project {{id: '{project_id}'}})-[:DEPENDS_ON]->(s:Service)<-[:DEPENDS_ON]-(p2:Project) "
    "WHERE p2 <> p "
    "RETURN p2.id "
    "$$) AS (id agtype);"
)
```

Which other projects share dependencies with this one? Then we fetch documents authored by those colleagues or belonging to those neighboring projects. This is the magic. A vector match on "payment service outage" brings back one incident report. Graph expansion pulls in the rest of the team who handled it, the adjacent services that depend on payments, and the architecture docs those other services produced. You go from one document to a little neighborhood of context without ever asking the LLM to be clever.

Stage three is where we clean up. The rerank function deduplicates by title (because vector and graph will often surface the same doc) and applies different weights depending on where each hit came from:

```python
for item in best_by_title.values():
    if item.source == "vector":
        combined_score = item.score * vector_weight
    elif item.source == "graph_expanded":
        combined_score = item.score * graph_weight
    else:
        combined_score = item.score
```

Default weights are 0.6 for vector and 0.4 for graph. Why those numbers? Because they worked in testing. That's it. That's the whole justification. You will absolutely want to tune these for your own data, and anyone who tells you there's a universal right answer is selling a vector database. The point of the weights isn't precision, it's intent: you're telling the system "semantic match is the main signal, structural proximity is the tiebreaker." Flip those weights and the behavior changes in interesting ways. Try it.

The reason this beats either strategy alone comes down to failure modes. Vector search fails when the question is structural (who, which team, what depends on what). Graph search fails when the question is semantic (what did we decide, what happened, how does this work). Combined search fails only when both fail, which in practice is rare, because almost every real question has at least one foothold in one world or the other.

## The LLM layer (it's honestly not the star)

The LLM interface is deliberately dumb:

```python
class LLMProvider(Protocol):
    def generate(self, prompt: str, context: list[str]) -> str: ...


def get_llm_provider(provider_name: str) -> LLMProvider:
    if provider_name == "claude":
        from llm.claude_llm import ClaudeLLMProvider
        return ClaudeLLMProvider()
    elif provider_name == "openai":
        from llm.openai_llm import OpenAILLMProvider
        return OpenAILLMProvider()
    elif provider_name == "ollama":
        from llm.ollama_llm import OllamaLLMProvider
        return OllamaLLMProvider()
```

Three providers. One environment variable to switch. Claude, OpenAI, or a local Ollama model running on your laptop. I don't care which one you use, and you probably shouldn't either. This is my hill to die on in AI Land: the hard problem is always data engineering, not model selection. Embedding models, chunking strategies, and search filtering will move your quality needle ten times further than arguing about whether Claude or GPT is smarter this week. The LLM takes whatever context you hand it and generates a response. If the context is good, the answer is good. If the context is garbage, no model will save you. (I've watched teams spend six weeks comparing frontier models when their retrieval was returning the wrong documents. Don't be that team.)

## The orchestrator (run them all, time them all)

To make the comparison fair, the FastAPI handler runs all three strategies in parallel using asyncio plus a thread pool:

```python
vector_future = loop.run_in_executor(
    _executor, _run_strategy, "vector", request.question, request.top_k
)
graph_future = loop.run_in_executor(
    _executor, _run_strategy, "graph", request.question, request.top_k
)
combined_future = loop.run_in_executor(
    _executor, _run_strategy, "graph+vector", request.question, request.top_k
)

results = await asyncio.gather(vector_future, graph_future, combined_future)
```

Each strategy gets its own timing object that captures every stage: embedding, vector search, entity extraction, graph traversal, graph expansion, reranking, LLM generation. Every millisecond gets a label. Parallel execution matters because we want apples-to-apples comparisons across strategies, not "the first one ran while the database was cold." We'll spend all of Part 3 staring at these numbers.

## What's next

We've got three retrieval strategies, one database, and a FastAPI endpoint that fires them off in parallel and times every stage. Part 3 is the showdown. We'll put all three head-to-head on real questions, look at where each one wins and where each one faceplants, and stare at the timing data until we have receipts. Spoiler: it gets interesting, and not always in the direction I expected.

Now the question for you. Before you read Part 3, take a guess: on an org-knowledge corpus like this one, how much slower is combined retrieval than vector-only? And does the answer change your mind about whether it's worth building? Write your guess down. I'll tell you if you were right next post.
