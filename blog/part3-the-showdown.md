# The Showdown: Vector vs Graph vs Graph+Vector

Time to put these three strategies in the ring. Same stack, same questions, three retrieval approaches, and differences you can actually measure. I've been building toward this moment for two blog posts and honestly? I was a little nervous the combined approach wouldn't pull its weight. Spoiler: it does, but not always, and the "not always" part is the interesting bit.

## Fire it up

If you've been following along, you already know the drill. From the `graphrag-demo` directory:

```bash
docker compose up --build
```

Give it a minute to seed. Then open `http://localhost:8000` in a browser.

What you'll see is pretty simple. A search bar at the top. Three columns underneath labeled Vector, Graph, and Combined. A row of example queries you can click so you don't have to type. Hit one, and all three columns fill in at the same time with whatever each strategy thinks is the right answer. No fancy animations. No loading spinners that lie to you. Just three retrieval paths racing for the same prize.

I built this demo app specifically to avoid the thing I hate about most RAG demos, which is that they show you the winning answer and hide everything else. I want you to see all three so you can judge for yourself when one beats the others and when they tie. Confession: my first version of this UI was a single answer box with a dropdown to pick the strategy. I stared at it for about an hour, felt dumb, and rewrote it as three columns. The comparison was the whole point and I'd almost hidden it behind a select element. Classic Yonk move.

The example queries at the top of the page are the four we're about to walk through. They're there because I wanted to pick queries that would make the tradeoffs obvious without cherry-picking. Two of them vector wins or ties. Two of them graph wins or changes the game. That's roughly the ratio I see in real workloads, and it's why "just use vector" is not a terrible default but also not the final answer.

## Query 1: "What was decided about the billing migration?"

Click it. Watch what happens.

Vector goes straight to the decision doc. The one titled "Billing Migration: Final Architecture Decision" with an embedding that lines up almost perfectly with the question. It pulls two or three adjacent chunks for context and hands back a clean answer about which database the team picked and why. Takes about 50 milliseconds total. It's not wrong. It's actually really good.

Graph struggles here. "Billing migration" is a project name in our knowledge graph, sure, but the question isn't asking about structure. It's asking about content. Graph finds the Billing Migration project node, walks to its owner team, pulls adjacent entities, and returns a bunch of metadata that doesn't actually answer the question. It's like asking your buddy what the score of the game was and he tells you the stadium's address.

Combined basically echoes vector. The vector hits dominate the ranking, the graph context gets used to boost one result, and the output looks nearly identical to the vector column. It costs more to produce the same answer.

Here's the honest take: if every question your users ask sounds like "what was decided about X," you don't need any of this. Vector-only is the right answer. It's cheap, it's fast, and it's built for exactly this. Close the tab. Go ship your feature. I'm not offended.

The graph stuff starts earning its keep when the questions get weirder.

## Query 2: "Who should I talk to about the payment service?"

This is the one that made me sit up straight the first time I ran it.

Vector returns three documents that mention payments. An old incident report about a payment gateway timeout. A runbook chunk about refund processing. A Slack export where somebody complained about Stripe webhooks. All related to payments. None of them tell you who to talk to. The word "owner" doesn't appear anywhere in the top results because nobody writes docs titled "Here Is The Owner Of The Payment Service, Please Email Them." That's not how humans write.

Graph does something completely different. It pulls "payment service" out of the question, matches it to the `Service` node named Payment Service, then walks one hop to find the `Team` that owns it. From the team node, it walks to the `Person` nodes who are members. It returns: Payment Service is owned by the Platform Engineering team. Alice is the team lead. Bob and Maya are the other engineers. There's your answer. In about 120 milliseconds, start to finish.

Combined puts both columns together and it's the best version of the answer. You get the ownership chain from the graph side (team, lead, engineers) and the three relevant docs from the vector side (past incidents, the runbook, the Slack context). So when you walk over to Alice's desk, you're not starting cold. You already know what's been going on with her service. That's the difference between "who do I ask" and "I'm prepared for this conversation."

Put the three columns side by side and you can literally watch the two retrieval styles argue with each other. Vector is pattern-matching text. Graph is walking a skeleton. Combined is doing both and merging. This query is the moment the demo earns its keep, and if you only run one query from the example list, run this one.

## Query 3: "What's the blast radius if the auth service goes down?"

Now we're playing the actual game.

Vector finds the historical incident reports. The time auth went down for 40 minutes in February and took the mobile app with it. The postmortem where somebody wrote "we should really map our dependencies someday." (We did. You're reading about it.) Useful context but not the answer. Vector can't tell you what's currently depending on auth because "depending on" is a relationship, not a phrase.

Graph walks the dependency edges. From the Auth Service node, it follows `DEPENDS_ON` edges in reverse to find everything that points at it. Payment Service depends on auth. Search depends on auth. Analytics depends on auth. Then from each of those services it walks one more hop: which projects are currently using Payment (Billing Migration), Search (Search Redesign), Analytics (Analytics Dashboard Q2). That's the blast radius. Three services, three projects, immediate downstream impact.

Combined stitches all of it together. Dependency chain from the graph. Incident history from the vector hits. Responsible humans from the graph (because you're gonna want to ping the Platform team and the Search team at the same time). You hit enter once and get an answer that would've taken you 15 minutes of Slack archaeology to assemble by hand.

Here's the timing breakdown on this query:

- **Vector:** ~50ms (embed 15ms, HNSW search 35ms)
- **Graph:** ~120ms (entity extract 5ms, AGE traversal 115ms)
- **Combined:** ~180ms (all of the above plus 60ms for graph expansion and result rerank)

The combined path costs about 130ms more than vector alone. For an incident response question where you're trying to figure out what's on fire, 180ms is nothing. You'd happily wait a full second for that answer. The cost only matters if you're serving it at Google scale, and if you're serving it at Google scale you have problems I can't help you with in a blog post.

## Query 4: "Catch me up on what the data team has been working on"

This one's for anyone who's ever prepped for a 1:1 at 9:57 AM for a 10:00 AM meeting.

Graph walks from the Data Team node through `MEMBER_OF` edges to find everyone on the team, then through `WORKS_ON` edges to find every project those people are attached to. Clean list. Five people, three projects, two cross-team collaborations. Done.

Vector finds a scatter of data-adjacent docs. The quarterly data platform review. A pull request description for the new dbt model. A meeting note where somebody mentioned the warehouse migration. All relevant, all disconnected, all pulled together by semantic similarity instead of structure.

Combined gives you the org picture (team, people, projects) plus the recent activity (docs, PRs, notes) plus the cross-team dependencies (who the data team has been trading tickets with). It's exactly the briefing you wanted when you typed the question. This is the use case where my RAG-skeptic friends get quiet, because "catch me up on X" is the query that generic chatbots have been failing at for two years and this is what actually fixes it.

## When to use what

Here's the cheat sheet. Print it, tape it to your monitor, whatever.

**Vector-only is the right answer when:**

- The question is semantic. "Find me the doc about X."
- You're doing FAQ retrieval, content search, or help-center stuff.
- You care about cost and latency more than completeness.

**Graph-only earns its keep when:**

- The question is structural. "Who owns this," "what depends on that."
- The question contains named entities your graph actually knows about.
- You're doing org lookups, dependency analysis, or impact planning.

**Combined is worth the extra 100ms when:**

- The question is investigative. "Catch me up," "what should I know about."
- The user doesn't know what they don't know yet.
- The answer matters enough that you'd rather get it right than get it fast.

And one rule that overrides all three: you don't have to pick one strategy for your whole app. Run multiple paths in parallel, merge the results, or let the user flip between them. The demo does exactly that. It's not hard. It's just that nobody bothers because the tutorials all show you one strategy at a time and you assume that's the shape of the world.

## Production considerations (the short version)

I'm not going to write a 3,000-word ops guide here. But if you're taking this from demo to prod, here's the stuff that'll bite you:

- **HNSW tuning.** The default `m` and `ef_construction` values are fine for 10,000 docs and wrong for 10 million. Tune for your dataset size or pay the recall tax.
- **Graph schema restraint.** Fewer edge types almost always beats many. I've seen teams ship graphs with 40 edge types and nobody could remember what any of them meant six months later. Start with five. Earn the sixth.
- **Cache entity lookups.** Graph queries for simple "find this entity by name" patterns are shockingly slow compared to a Redis hit. Cache them.
- **Batch your embeddings when seeding.** One embedding API call per doc is how you turn a 10-minute seed into an afternoon.
- **Push work into AGE when the graph gets huge.** If you're doing traversals in Python that Cypher could do in one query, stop. The app server is not where graph math should live.

That's it. The rest you'll learn by breaking things, which is how I learned it too.

## Your turn

Your RAG pipeline right now is almost certainly vector-only. I know this because I've looked at maybe 30 production RAG systems in the last year and all but two of them were vector-only. It's the default. It's not wrong. But I want you to do one thing for me.

Go look at your query logs. Pull the questions your users are actually asking. I bet at least 20% of them are structural ("who," "what depends on," "catch me up"), and I bet your current pipeline is answering those badly or not at all. Those are the questions a graph can eat for breakfast. That's where this matters. Not everywhere. Just where it matters.

So clone the demo. Point it at your own data. Break it in ways I didn't think of. Find the query where graph+vector produces something you couldn't get any other way, and then go tell somebody on your team about it. Or tell me. I want to know what you find, especially the failures, because the failures are where the next blog post lives.

Oh, and if you build something cooler than my three-column demo, don't make me find out about it on Hacker News six months from now. Ping me. The HOSS wants to see it.

Now go break some stuff.
