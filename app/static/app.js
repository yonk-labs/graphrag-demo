const STAGE_COLORS = {
    embedding: "#f59e0b",
    vector_search: "#3b82f6",
    entity_extraction: "#8b5cf6",
    graph_traversal: "#6366f1",
    graph_expansion: "#10b981",
    reranking: "#ec4899",
    llm_generation: "#ef4444",
};

const STAGE_LABELS = {
    embedding: "Embed",
    vector_search: "Vector Search",
    entity_extraction: "Entity Extract",
    graph_traversal: "Graph Traverse",
    graph_expansion: "Graph Expand",
    reranking: "Re-rank",
    llm_generation: "LLM",
};

document.addEventListener("DOMContentLoaded", loadExamples);

document.getElementById("question-input").addEventListener("keydown", function(e) {
    if (e.key === "Enter") runQuery();
});

async function loadExamples() {
    try {
        const resp = await fetch("/api/examples");
        const examples = await resp.json();
        const container = document.getElementById("example-buttons");
        examples.forEach(function(ex) {
            const btn = document.createElement("button");
            btn.className = "example-btn";
            btn.textContent = ex.question;
            btn.title = ex.description;
            btn.onclick = function() {
                document.getElementById("question-input").value = ex.question;
                runQuery();
            };
            container.appendChild(btn);
        });
    } catch (err) {
        console.error("Failed to load examples:", err);
    }
}

async function runQuery() {
    const input = document.getElementById("question-input");
    const question = input.value.trim();
    if (!question) return;

    const btn = document.getElementById("search-btn");
    btn.disabled = true;

    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("results").classList.add("hidden");

    try {
        const resp = await fetch("/api/query", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question: question, top_k: 10}),
        });

        if (!resp.ok) throw new Error("Query failed: " + resp.status);

        const data = await resp.json();
        renderResults(data);
    } catch (err) {
        console.error("Query error:", err);
        alert("Query failed. Check the console for details.");
    } finally {
        btn.disabled = false;
        document.getElementById("loading").classList.add("hidden");
    }
}

function renderResults(data) {
    data.strategies.forEach(function(strategy) {
        renderTiming(strategy.strategy, strategy.timing);
        renderAnswer(strategy.strategy, strategy.answer);
        renderResultsList(strategy.strategy, strategy.results);
    });

    document.getElementById("results").classList.remove("hidden");
}

function renderTiming(strategyName, timing) {
    const container = document.getElementById("timing-" + strategyName);
    if (!container) return;

    const total = timing.total || 0;
    const stages = Object.entries(timing).filter(function(entry) {
        return entry[0] !== "total";
    });

    let html = '<div class="timing-stages">';
    stages.forEach(function(entry) {
        const name = entry[0];
        const ms = entry[1];
        const pct = total > 0 ? (ms / total) * 100 : 0;
        const color = STAGE_COLORS[name] || "#6b7280";
        const label = pct > 15 ? Math.round(ms) + "ms" : "";
        html += '<div class="timing-stage" style="width:' + pct + '%;background:' + color + '">' + label + '</div>';
    });
    html += '</div>';
    html += '<div class="timing-total">' + Math.round(total) + 'ms total</div>';

    html += '<div class="timing-legend">';
    stages.forEach(function(entry) {
        const name = entry[0];
        const ms = entry[1];
        const color = STAGE_COLORS[name] || "#6b7280";
        const label = STAGE_LABELS[name] || name;
        html += '<span class="legend-item"><span class="legend-dot" style="background:' + color + '"></span>' + label + ': ' + Math.round(ms) + 'ms</span>';
    });
    html += '</div>';

    container.innerHTML = html;
}

function renderAnswer(strategyName, answer) {
    const container = document.getElementById("answer-" + strategyName);
    if (!container) return;

    container.innerHTML = '<div class="answer-label">Generated Answer</div><div>' + escapeHtml(answer) + '</div>';
}

function renderResultsList(strategyName, results) {
    const container = document.getElementById("results-" + strategyName);
    if (!container) return;

    if (!results || results.length === 0) {
        container.innerHTML = '<div class="no-results">No results found</div>';
        return;
    }

    let html = "";
    results.slice(0, 5).forEach(function(item) {
        html += '<div class="result-item">';
        html += '<div class="result-title">' + escapeHtml(item.title) + '</div>';
        html += '<div class="result-meta">';
        html += '<span class="result-score">Score: ' + item.score.toFixed(4) + '</span>';
        html += '<span class="result-type">' + item.doc_type + '</span>';
        html += '</div>';
        html += '<div class="result-explanation">' + escapeHtml(item.explanation) + '</div>';
        html += '<div class="result-content">' + escapeHtml(item.content.substring(0, 200)) + '</div>';
        html += '</div>';
    });

    container.innerHTML = html;
}

function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
