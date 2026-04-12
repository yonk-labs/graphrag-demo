"""
Content templates for SCOTUS-style documents.

Key insight: majority opinions and dissents deliberately avoid naming the
case, the parties, or the voting justices. That information lives in the
graph, not the text. Case summaries are more vector-friendly.
"""

SUMMARY_TEMPLATES = [
    (
        "{case_name}: Case Summary",
        "In {case_name}, decided in {term}, the Court addressed a question of "
        "{issue}. The petitioner argued {petitioner_arg}. The respondent "
        "countered that {respondent_arg}. By a {vote_split} vote, the Court "
        "{outcome}. Justice {majority_author} delivered the opinion of the Court. "
        "{dissent_author_clause}"
    ),
    (
        "{case_name} ({term})",
        "This term the Court heard {case_name}, a case arising under {issue}. "
        "The dispute began when {petitioner_arg}, while the opposing party "
        "maintained that {respondent_arg}. In a {vote_split} decision, the "
        "judgment below was {outcome}. The opinion was authored by Justice "
        "{majority_author}. {dissent_author_clause}"
    ),
    (
        "Summary: {case_name}",
        "{case_name} presented the Court with a significant question touching on "
        "{issue}. Petitioner's central contention was that {petitioner_arg}. "
        "Respondent took the position that {respondent_arg}. The Court, dividing "
        "{vote_split}, {outcome} the decision below in an opinion by Justice "
        "{majority_author}. {dissent_author_clause}"
    ),
]

MAJORITY_OPINION_TEMPLATES = [
    (
        "Opinion of the Court",
        "The question before the Court is whether {legal_question}. We hold "
        "that {holding}. The long-standing principle established in earlier "
        "precedents requires us to consider {doctrine}. Applying this framework, "
        "we find that the lower court {lower_court_outcome}. The dissent contends "
        "{dissent_counter}, but we believe this reading is inconsistent with "
        "{precedent_reference}. Accordingly, we {disposition}."
    ),
    (
        "Opinion of the Court",
        "This case requires us to decide whether {legal_question}. After careful "
        "review of the record and the parties' arguments, we conclude that "
        "{holding}. Our analysis begins with {doctrine}, a principle deeply "
        "rooted in our jurisprudence. The court below {lower_court_outcome}, and "
        "though respondents urge {dissent_counter}, such a reading would be "
        "difficult to square with {precedent_reference}. We therefore {disposition}."
    ),
    (
        "Opinion of the Court",
        "We granted certiorari to resolve whether {legal_question}. Today we "
        "answer that question and hold {holding}. Central to our reasoning is "
        "{doctrine}. In the proceedings below the court {lower_court_outcome}. "
        "While it has been argued {dissent_counter}, this position cannot be "
        "reconciled with {precedent_reference}. The Court accordingly {disposition}."
    ),
]

DISSENT_TEMPLATES = [
    (
        "Dissenting Opinion",
        "I respectfully dissent. The majority's holding today {critique} and "
        "departs from our established precedent in {precedent_ref}. The "
        "fundamental question is not {framing_majority} but rather {framing_dissent}. "
        "History and tradition make clear that {historical_claim}. I would instead "
        "{alternative_outcome}. The implications of today's decision extend far "
        "beyond the facts of this case, potentially affecting {broader_impact}."
    ),
    (
        "Dissenting Opinion",
        "I must dissent. Today's decision {critique}, and in doing so ignores "
        "the careful balance struck by {precedent_ref}. The majority frames the "
        "issue as {framing_majority}, but that is not the inquiry our cases "
        "demand. The real question is {framing_dissent}. {historical_claim}. "
        "I would {alternative_outcome}, and I fear the Court's path will reshape "
        "{broader_impact}."
    ),
    (
        "Dissenting Opinion",
        "With respect, I cannot join the Court's opinion. The majority {critique} "
        "and effectively overrules {precedent_ref} without saying so. Where the "
        "Court sees {framing_majority}, the correct lens is {framing_dissent}. "
        "{historical_claim}. The better course is to {alternative_outcome}. The "
        "consequences will be felt for years in {broader_impact}."
    ),
]

# --- Placeholder phrase pools ---

PETITIONER_ARGS = [
    "the agency exceeded its statutory authority",
    "the lower court misapplied controlling precedent",
    "the challenged statute violates constitutional guarantees",
    "the government's interpretation sweeps too broadly",
    "longstanding practice supports a narrower reading",
    "the text of the statute unambiguously forecloses the government's position",
    "the injury alleged is concrete and redressable",
    "the regulation imposes burdens Congress never authorized",
    "the decision below conflicts with sister circuits",
    "due process requires additional procedural protection",
]

RESPONDENT_ARGS = [
    "the agency acted well within its delegated authority",
    "the decision below faithfully applied this Court's precedents",
    "the statute is a valid exercise of legislative power",
    "any narrower reading would frustrate the statute's purpose",
    "the challenger lacks standing to bring this claim",
    "the interpretation is entitled to deference",
    "the claim is barred by sovereign immunity",
    "the burden on the challenger is incidental at most",
    "longstanding administrative practice supports the decision",
    "the text and structure of the statute clearly permit the action",
]

LEGAL_QUESTIONS = [
    "the First Amendment's Free Exercise Clause permits such a burden on religious practice",
    "federal antitrust law preempts state-level regulation in this context",
    "the Fourth Amendment requires a warrant for this category of search",
    "the agency's interpretation is entitled to Chevron deference",
    "due process requires an additional procedural safeguard in these circumstances",
    "the Commerce Clause authorizes Congress to regulate the conduct at issue",
    "the statute's savings clause preserves state-law remedies",
    "sovereign immunity bars the suit brought in federal court",
    "the challenged practice violates the Equal Protection Clause",
    "the statute of limitations began to run at the time of injury",
]

HOLDINGS = [
    "it does not, and the judgment below must be set aside",
    "it does, and we affirm the court of appeals",
    "the text of the statute compels the opposite conclusion",
    "neither the history nor the structure of the provision supports such a reading",
    "the answer turns on a narrower ground than the parties contemplated",
    "the constitutional question need not be reached",
    "the agency's construction is reasonable and must be upheld",
    "the lower court's analysis cannot be reconciled with our cases",
    "the proper remedy is remand for further proceedings",
    "the challenger has failed to establish the predicate injury",
]

DOCTRINES = [
    "the canon against constitutional avoidance",
    "the presumption against retroactive application",
    "the rule of lenity in criminal statutes",
    "the traditional limits on judicial review of agency action",
    "the framework established by our longstanding precedents",
    "the text, structure, and history of the provision",
    "the ordinary meaning of the statutory language",
    "the constitutional principle of separation of powers",
    "the background rules of sovereign immunity",
    "the due process requirement of fair notice",
]

LOWER_COURT_OUTCOMES = [
    "reached the right result for the wrong reasons",
    "misread the governing statute",
    "erred in its application of the relevant test",
    "correctly identified the controlling precedent",
    "failed to address a threshold jurisdictional question",
    "relied on authority that has since been overtaken",
    "committed harmless error in its evidentiary rulings",
    "adopted a framework inconsistent with this Court's cases",
    "got the ultimate question right despite some missteps",
    "overlooked the statutory text's plain meaning",
]

DISSENT_COUNTERS = [
    "that our precedents compel the opposite result",
    "that the text is more ambiguous than we acknowledge",
    "that history points in a different direction",
    "that the Court's rule will prove unworkable in practice",
    "that the majority oversteps the judicial role",
    "that Congress did not intend so sweeping a reading",
    "that the tradition points unmistakably the other way",
    "that the ruling will invite a flood of litigation",
]

PRECEDENT_REFERENCES = [
    "our long line of cases on the subject",
    "the framework we articulated decades ago",
    "the principles enshrined in our landmark decisions",
    "the tradition reflected in Anglo-American law",
    "the original public meaning of the provision",
    "the text and structure of the Constitution",
    "our most recent pronouncements on the question",
    "the settled understanding of the doctrine",
]

DISPOSITIONS = [
    "reverse and remand for further proceedings",
    "affirm the judgment of the court of appeals",
    "vacate and remand with instructions",
    "reverse the decision below",
    "affirm in part and reverse in part",
    "dismiss the writ as improvidently granted",
    "remand for consideration in light of this opinion",
]

CRITIQUES = [
    "rewrites the statute under the guise of interpretation",
    "abandons a rule we have applied for generations",
    "substitutes the Court's policy preferences for the judgment of Congress",
    "erodes a constitutional protection the Framers thought essential",
    "adopts a test no lower court will find administrable",
    "misreads both the text and the history of the provision",
    "sweeps far more broadly than the facts of this case require",
    "ignores the practical consequences of its holding",
]

FRAMINGS = [
    "whether the statute permits the challenged conduct",
    "whether the lower court correctly applied the test",
    "whether the Constitution tolerates this intrusion",
    "whether the agency's view deserves deference",
    "whether the challenger has cleared the standing threshold",
    "whether history supports the asserted right",
    "whether the statute's text resolves the question",
    "whether the Court should reach the constitutional issue at all",
]

HISTORICAL_CLAIMS = [
    "the Framers understood this provision to mean something quite different from what the Court announces today",
    "at the time of the founding, such a practice would have been plainly understood as lawful",
    "for over a century our cases have read the provision the other way",
    "the tradition of the common law pointed in the opposite direction",
    "Reconstruction-era understandings of this guarantee were far broader than the majority suggests",
    "the earliest decisions interpreting this clause confirm the narrower reading",
]

ALTERNATIVE_OUTCOMES = [
    "affirm the judgment below on the grounds the court of appeals gave",
    "remand for reconsideration under the correct legal standard",
    "dismiss the petition for want of jurisdiction",
    "hold that the challenger has not met its burden",
    "reach the constitutional question and decide it the other way",
    "apply the traditional test rather than the majority's novel framework",
]

BROADER_IMPACTS = [
    "countless administrative proceedings across the federal government",
    "the delicate balance between federal and state authority",
    "the rights of litigants in both civil and criminal cases",
    "First Amendment protections we have long taken for granted",
    "the scope of congressional power under Article I",
    "the Court's own legitimacy as a neutral arbiter",
    "entire industries that have relied on the prior rule",
    "the everyday work of trial courts nationwide",
]
