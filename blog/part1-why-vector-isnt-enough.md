# Why Your RAG Pipeline Needs Graph AND Vector AND Hybrid Search

So you built a RAG pipeline. You stacked pgvector on top of Postgres, wired it to an embedding model, hooked it to your favorite LLM, and shipped it to a handful of real users. For a week you felt like a wizard. Then somebody asked, "who voted with Sotomayor on First Amendment cases last term?" and your shiny system coughed up three dissent paragraphs that don't actually name a single justice. Your users stopped asking clever questions and started asking, politely, whether the whole thing is broken.

I've built this exact broken thing. More than once. (I'm not proud of it, but pretending otherwise would be a bad look for someone who's been working on databases for 20+ years.) The reason it keeps happening isn't that vector search is bad. Vector search is great at what it does. The problem is that your users don't ask one kind of question. They ask three. And if you only built for one, two out of three queries are going to make you look silly.

## Three kinds of questions, three kinds of retrieval

Here's the deal. Every production RAG system I've looked at eventually runs into the same split. Users ask semantic questions, they ask keyword questions, and they ask relationship questions. Those aren't marketing buckets I made up on a whiteboard. They're the three shapes real queries take, and each shape needs a different retrieval technique to answer it well.

**Kind 1: "Find me something like this."** The user has a vibe, a topic, a concept. They don't know the exact words in the document, and they don't care. "What cases deal with administrative overreach?" is a semantic question. The phrase "administrative overreach" might not appear anywhere in the actual ruling, but the concept does. This is exactly what vector search was built for. You embed the query, you embed the documents, you run a cosine similarity lookup, and pgvector hands you back the top matches in milliseconds. It doesn't care about exact wording. It cares about meaning.

**Kind 2: "Find me exactly this."** Now the user wants a specific string. A case number. An error code. A product SKU. A legal citation like `410 U.S. 113`. Vector search is surprisingly bad at this, because embedding models round off rare tokens. The numbers and codes that matter most to your users are the tokens the model has the least signal on. Hybrid search is the answer here, combining vector similarity with old-school full-text matching. Postgres ships `tsvector` and `tsquery` for free, and BM25 is a solved problem. Use it. If you need to find docket number 17-204, you want a keyword hit, not a vibe.

**Kind 3: "Show me how these things connect."** This is the one that breaks RAG systems in demos. The user wants structure. "Which justices tend to vote together on civil rights cases?" "What upstream services depend on the auth service?" "Who reports to the VP of Engineering?" The answer isn't hiding in a document somewhere. The answer lives in the edges between entities. You can't find it by similarity, and you can't find it by keyword, because it was never written down as text in the first place. You need a graph. Apache AGE lets you run Cypher inside Postgres and do multi-hop pattern matches without bolting on another database.

So what does that actually mean for your architecture? It means every serious RAG system eventually needs all three retrieval paths. The only real question is whether you wire them up on purpose, now, or whether you wire them up at 2 AM after a demo goes sideways.

## Why most teams only build one

Let's be honest about why this happens. Vector search is easy. There's a tutorial for it on every blog, including probably one I wrote. Hybrid search is a little harder, but it's well-documented and every Postgres shop already has `tsvector` in their back pocket whether they know it or not. Graph databases, though, feel foreign. They get dismissed with, "we don't need another database to babysit."

I get it. I was that guy. For years I pushed back hard on adding more datastores to production stacks, because I've watched teams drown in their own infra choices. One Postgres cluster with backups and monitoring is a known problem. Three different datastores with three different failure modes is a new job.

Here's what I missed. You don't actually need another database. Apache AGE is a Postgres extension. pgvector is a Postgres extension. Full-text search is built in. You can run all three retrieval paths inside one Postgres 16 instance, with one backup job, one monitoring dashboard, and one on-call pager. I spent years telling people not to add more databases, and then I sat down to build this demo and realized the thing I was most worried about (running AGE and pgvector in the same cluster) was the easy part. The hard part, as always, was figuring out which retrieval technique to use when. Data engineering, not database selection. I guess I'm consistent if nothing else.

## When each technique wins, and when it falls on its face

Abstract arguments are fine, but let me show you three real queries from the SCOTUS demo we built, because it makes the split obvious.

**Query 1: "Find cases about administrative overreach."** Vector search crushes this. The phrase "administrative overreach" probably isn't in the opinions verbatim, but the concepts ("arbitrary and capricious," "Chevron deference," "agency action") live in the same semantic neighborhood. A cosine similarity search over a pgvector index returns the right cases on the first try. Hybrid adds a little precision. Graph is basically useless here, because the answer isn't about which entities are connected, it's about what the documents mean. Vector-only is good enough, and you'd be wasting compute running the other paths.

```sql
SELECT case_name, 1 - (embedding <=> query_embedding) AS similarity
FROM cases
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

**Query 2: "Find the case with docket number 17-204."** Now vector fails. `17-204` doesn't carry meaningful embedding signal, and the model compresses it into something close to the general idea of "numbers in a legal document." You'll get a bunch of cases that mention docket numbers, just not the one you asked for. Hybrid search saves you here, because `tsquery` matches the exact token and ranks it first. This is a one-line win, and it's the reason I still tell people to turn on full-text search even when they think they don't need it.

**Query 3: "Which cases did Justice Thomas and Justice Sotomayor vote together on?"** This is the money query. Vector search returns documents that talk about voting. Hybrid search returns documents that mention both names. Neither actually answers the question, because the answer isn't in any single document. It lives in the edges between Justice nodes and Case nodes in the graph. One Cypher query does what vector and hybrid cannot do at any cost:

```cypher
MATCH (j1:Justice {name: 'Clarence Thomas'})-[:VOTED_MAJORITY]->(c:Case)
      <-[:VOTED_MAJORITY]-(j2:Justice {name: 'Sonia Sotomayor'})
RETURN c.case_name, c.decided
ORDER BY c.decided DESC;
```

That's a multi-hop pattern match across typed edges. Vector and hybrid cannot express this query, period. Not slowly, not with clever prompting, not at all. If your users ever ask questions that require reasoning over relationships between entities, a graph isn't a nice-to-have. It's the only thing that works.

## How we built the demo

The stack is deliberately boring, which is the point. Postgres 16 with pgvector and Apache AGE, both built from source and baked into one image. A FastAPI orchestrator that runs all four retrieval paths in parallel (vector only, hybrid, graph only, and a combined path that merges them with reranking). A side-by-side UI that shows exactly what each approach returns for the same question, so you can see the split with your own eyes instead of taking my word for it. One Postgres cluster. One ops footprint. No hand-waving.

The dataset is real. 391 Supreme Court cases from 2018 through 2023, with justice votes, majority opinions, dissents, and citations modeled as graph edges. We also ship a synthetic Acme Labs org knowledge base example for people who want to see the same pattern on corporate-style data without the legal vocabulary. Both run on the same stack, and both make the three-question split painfully obvious. The repo is public. Pull it, run it, and ask it the questions your users actually ask you.

The reason we run all four paths in parallel in the demo, instead of routing queries to one path, is that routing is itself a hard problem. Query classification is brittle. Users write ambiguous prompts that look semantic but need a graph, or look like graph questions but are really keyword lookups in disguise. Running them all and comparing results is the cheapest way I've found to learn what your users are actually asking and which path pays off for which query. Once you have that data, you can build a smarter router. Before you have it, any router you build is just a guess wearing a lab coat. And guessing about user intent is the fastest way I know to end up with a RAG system that looks great in the sales deck and falls over the first time somebody clicks around.

## What's coming in Parts 2 and 3

Part 2 is the setup guide. How to build Postgres 16 with AGE and pgvector from source (because the packaged builds don't always line up), how to bring up the Docker Compose stack, and how to run your first Cypher query and your first vector query to prove the thing is alive. It's the "I just want to get this running on my laptop before lunch" post.

Part 3 is the replication walkthrough. How we built the SCOTUS parser, how we designed the graph schema (justices, cases, votes, citations, and the tradeoffs in each), how we added multi-hop query detection so the orchestrator knows when to reach for Cypher, and how to adapt the whole thing to your own dataset. If you want to build your own GraphRAG system on top of this pattern, Part 3 is the one to bookmark.

## Your homework

Your RAG pipeline probably answers two out of three kinds of questions today. Which one is it missing? Go find out. Run the demo, point it at the SCOTUS data, and ask it the stuff your actual users ask. If it falls apart on the relationship questions, you know what you're missing. If it fumbles the exact-match keyword questions, you know what you're missing. The worst answer is "I don't know which ones I'm missing," because that's the version where you find out in production with a Slack thread full of angry users.

Me, I'll be over here running Cypher inside Postgres and pretending I always thought graphs were a good idea. Don't tell anyone I used to argue the other way.
