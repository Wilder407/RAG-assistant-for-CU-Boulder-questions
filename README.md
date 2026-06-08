# The Unofficial Guide — Project 1


## Domain

<!-- What topic or category of knowledge does your system cover? -->

The domain for my Unofficial Guide is things you wouldn't learn on an official campus tour. 
The domain sits at an interesting intersection — it's part local history, part campus life 
guide, part folklore archive, and part nature and art tour. Users might approach it from 
very different angles: a curious freshman, a prospective student, a visiting parent, or even
 a longtime Buff who thinks they know everything. 

This knowledge is valuable because it allows a student to fully immerse in the uniqueness of 
the Historic University of Colorado Boulder campus. Resources are scatterd across newspaper 
articles, campus webpages, reddit forums. This unoffical guide brings together traditions, 
tucked-away study spots, and overlooked museums that define life at one of the most 
architecturally striking campuses in the country — set against the backdrop of the Flatirons 
and Boulder's outdoor culture.
The campus celebrated 150 years which prompted me to consider all the stories, secrets, 
adventure and art that remain within the walls,waiting for a student to uncover it. 

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Type | URL or file path | Notes |
|---|--------|------|-----------------|-------|
| 1 | CU Independent | Article | https://cuindependent.com/2007/01/28/history-behind-the-name-cus-famous-monikers/ | |
| 2 | HerCampus | Article | https://www.hercampus.com/school/cu-boulder/hidden-gems-to-study-at-cu-boulder/ | |
| 3 | AboutBoulder | Article | https://aboutboulder.com/blog/exploring-the-hidden-gems-university-of-colorados-top-off-the-beaten-path-attractions/ | |
| 4 | CU Boulder Student Life | Website | https://www.colorado.edu/today/2020/01/30/your-guide-campus-venues-museums-and-more | |
| 5 | Visit Boulder | List/Map | https://www.bouldercoloradousa.com/things-to-do/visiting-cu/things-to-do-at-cu/ | JS-rendered; split into 5 inline caption entries |
| 6 | Coloradan Alumni Magazine | Article | https://colorado.edu/coloradan/2021/01/21/10-plants-and-animals-spot-campus | |
| 7 | CU Independent | Article | https://www.cuindependent.com/2013/10/24/secret-tunnels-and-murder-the-not-so-scary-truth/ | |
| 8 | Coloradan Alumni Magazine | Article | https://www.colorado.edu/coloradan/2010/09/01/unlocking-cu-secrets | |
| 9 | BASIN | Text | https://bcn.boulder.co.us/basin/watershed/geology/historic.html | |
| 10 | Daily Camera | Newspaper | https://www.dailycamera.com/2009/08/13/cu-student-murdered-40-years-ago-honored/ | Replaced Medium article (blocked) |
| 11 | AboutBoulder | Article | https://aboutboulder.com/blog/old-main-at-cu-boulder-history-flatirons-views-fun-facts/ | |
| 12 | Reddit | Forum Thread | https://www.reddit.com/r/whatisit/comments/1rwtvbg/comment/ob2cvjy/ | Duplicate of #14 — removed |
| 13 | Reddit | Forum Thread | https://www.reddit.com/r/cuboulder/comments/w0ylxm/what_are_some_good_hidden_places_or_resource/ | 403 blocked; content inlined manually |
| 14 | Reddit | Forum Thread | https://www.reddit.com/r/whatisit/comments/1rwtvbg/comment/ob2cvjy/ | Duplicate of #12 — removed |
| 15 | Reddit | Forum Thread | https://www.reddit.com/r/cuboulder/comments/1stfz3m/whats_a_free_thing_to_do_in_boulder_that_most_cu/ | 403 blocked; content inlined manually |
| 16 | CU Independent | Article | https://www.cuindependent.com/2016/02/05/the-story-behind-the-naming-of-the-dalton-trumbo-fountain/ | 403 blocked; replaced with inline content from colorado.edu sources |
| 17 | CU Campus Master Plan | Article | https://www.colorado.edu/masterplan/history/klauder-years-1918-1939 | |
| 18 | CU 150th Anniversary | Article | https://www.colorado.edu/150/cu-boulder-student-life-through-decades | |
| 19 | CU Alumni Association | Article | https://www.colorado.edu/alumni/2026/04/15/top-10-cu-boulder-traditions-bring-buffs-together | |

## Chunking Strategy

For newspaper articles and webpages, I will use a chunk size of **300 tokens** with a **75-token overlap**. These documents are typically focused on a single subject. At 300 tokens, each chunk should capture one complete idea without pulling in unrelated content. The 75-token overlap ensures that sentences straddling a boundary remain retrievable from either side.

For Reddit comments and short student-written posts, I will use a chunk size of **150 tokens** with a **30-token overlap**. These sources are already compact and conversational. Larger chunks would group unrelated tips or comments together and reduce retrieval precision.

For map captions and single-line entries, I will keep each entry as **one chunk with no splitting**, typically 30–80 tokens. These inputs are already self-contained units of meaning. Instead of overlap, I will attach structured metadata — including place name, source URL, and category — so retrieval has enough signal to surface them correctly.

---

| Document type | Chunk size | Overlap | Splitting |
|---|---|---|---|
| Articles and webpages | 300 tokens | 75 tokens | Yes |
| Reddit / short posts | 150 tokens | 30 tokens | Yes |
| Map captions | 30–80 tokens | None | No |

---

**Final chunk count:**

cu_boulder_guide consists of 95 chunks stored in the ChromaDB directory. 

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**

multi-qa-mpnet-base-dot-v1

**Production tradeoff reflection:**

The original model selected was all-mpnet-base-v2 via sentence-transformers. This was chosen over all-MiniLM-L6-v2 specifically to avoid its 256-token chunk size limit, which would have caused silent truncation on the longer article and webpage chunks in this corpus.

During evaluation, retrieval quality was tested using five natural language questions drawn from the evaluation plan. Chunk sizes and overlap were correct per spec, but returned chunks were frequently off-topic — for example, a query about the Dalton Trumbo Fountain returned a chunk mentioning Norlin Quad rather than the fountain's history. Cosine distances were consistently above 0.5 across all three tested queries, indicating weak alignment between the query embeddings and the stored chunk embeddings.

The root cause was a vocabulary mismatch inherent to all-mpnet-base-v2: it was trained on general sentence similarity rather than question-to-passage matching. When a user types a natural language question, the embedding lands in a different region of the vector space than a declarative sentence in a news article — even when both are about the same topic.

The model was upgraded to multi-qa-mpnet-base-dot-v1, which was trained on question-answer pair datasets including MS MARCO. This model is specifically optimized to close the gap between how questions are phrased and how answers are written in documents. After switching, retrieved chunks were measurably more relevant across all eval queries.

This iteration was anticipated in the original spec, which noted the upgrade as defensible for a question-answering system. Seeing the failure mode in practice — correct chunk sizes, wrong content — made the distinction between general-purpose and QA-optimized embedding models concrete rather than theoretical.

I also use eval query refinement as a related finding — changing "What ghost story is associated with Macky Auditorium?" to "Was there a murder at Macky Auditorium?" improved retrieval because the second phrasing shares vocabulary with how the source articles are written. This is a known limitation of dense retrieval that a hybrid search approach (combining vector similarity with keyword matching) would address in a production system.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

I provide these instructions to the AI:
- The output format (answer + source list).
- Source attribution is required either with a source source immediately following the response or by appending source information after generation
- I informed the AI to ensure that the LLM didn't generate an output based on the training data and instead only provided responses from the source documentation. 

**How source attribution is surfaced in the response:**

The Gradio UI has a box containing the source document links. The output is a few sentences instead of bullet points. Having this summary view supports a clearer user experience. It also may encourage the user to click and discover other facts.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 |  What is the history behind the Dalton Trumbo Fountain? | The fountain was built in 1964 and rededicated in 1993 to honor CU alum Dalton Trumbo, a Hollywood screenwriter who was blacklisted during the McCarthy era. Kirk Douglas helped break the blacklist by crediting Trumbo for Spartacus. The fountain is a free speech gathering space in front of the UMC. | The Dalton Trumbo Fountain, located at Norlin Quadrangle, was rededicated in 1993 to honor CU Boulder alumnus and blacklisted Hollywood screenwriter Dalton Trumbo. It serves as a designated free speech space and hub for student protests. | Relevant | Accurate |
| 2 | Was there a murder in Macky Auditiorium? | In 1966, music student Elaura Jaquette was murdered by janitor Joseph Dyre Morse in room 304. Students have reported hearing phantom organ music despite the organ being removed. There is a memorial plaque for her in the Norlin Quadrangle. | Yes, there was a murder in Macky Auditorium. Elaura Jaquette, a 20-year-old CU student, was brutally murdered there in the summer of 1966 by Joseph Dyer Morse. Her lunch, books, and billfold were found by police near a spot in the grass on the west side of Norlin Quadrangle, where she had been before being lured to the auditorium. | Relevant | Accurate|
| 3 | What wildlife can you spot on campus? |  Raccoons, deer, squirrels, beavers, prairie dogs, hawks, foxes, coyotes, and occasional bears (notably during fall move-in 2019). Turtles can be seen at Varsity Lake and Kittredge ponds. The campus also has a 10,000 sq ft pollinator garden with lavender and wildflowers. | Campus wildlife includes bears, raccoons, squirrels, turtles, deer, and prairie dogs. Keep a safe distance from animals, especially bears and raccoons, as they can be unpredictable. | Partially relevant | Accurate |
| 4 | What are some lesser-known study spots that aren't Norlin Library? | UMC 5th floor lounge (Flatirons views), Environmental Design Building, Duane Physics top floor, BioLounge in the Museum of Natural History, Koenig Alumni Center living room, Gemmill Library, and the Mindfulness room on Norlin's first floor. | Beyond Norlin Library, good study spots include the UMC student lounge and study rooms, Wolf Law and Koelbel libraries, the Aerospace Engineering building on East Campus, and the BioLounge in the CU Museum of Natural History (Henderson Building). | Partially relevant | Accurate |
| 5 | Tell me about Varsity Lake. | Before 1888, the area was a muddy ravine channeling snowmelt. In 1880 the student newspaper predicted a lake could be built there cheaply. A dam was built in 1888 forming Varsity Lake. Water lilies were recently reintroduced by a campus landscape architect inspired by old photos. | Varsity Lake is a beautiful spot on the CU Boulder campus, often referred to as a scenic pond. It's home to turtles that can be spotted sunning on rocks, and water lilies have been reintroduced to the area by a campus landscape architect who was inspired by historic photos. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

Is Macky Auditorium haunted?

**What the system returned:**

"I don't have enough information on that in my current sources."
Three resource links were provided related to the murder of Elaura Jaquette. 

**Root cause (tied to a specific pipeline stage):**

Certain documents that were in the original source collection were blocked (CU Independent articles). Since the articles that can be scraped don't make reference to the buidling bring haunted, the Guide informs the user that there isn't enough information. 

**What you would change to fix it:**

It's possible with additional time that the code could be updated to work with Java-script based sites given their popularity. 

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

The spec was very helpful since it provided a strong framework that allowed Claude to quickly and accurately write code to meet the requirements. I really appreciated how the eval questions were written into the spec since I am guilty of trying to just make the code run and work. Especially with this type of project, there really isn't success without evaluating along the way -- if the ingest stage is not producing the correctly sized chunks (or no chunks due to blocked conent), then the retrieval will also be poor. 

**One way your implementation diverged from the spec, and why:**

Due to java-script rendered pages, Claude suggested that certain articles like Visit Boulder be broken into smaller captions. This diverges from the spec sheet. A similar issue also occured for the Reddit sources but these were updated to be inline text given the 403 error at scraping. 
Mentioned earlier, the embed model was updated from all-mpnet-base-v2 to multi-qa-mpnet-base-dot-v1. This changed how the distances were managed: all-mpnet-base-v2 uses cosine distance and multi-qa-mpnet-base-dot-v1 uses dot distance. These models are trained differently and upgrading to the multi-qa-mpnet-base-dot-v1 supported the Query/Response model of my Guide. 

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
I gave the AI the planning.md document and the instuctions to generate the chunking and ingest code. The spec sheet included the source documents, the embed library, recommendations for the chunk size per source type and top-k retrieval number. 
- *What it produced:*
The AI produced a very strong and solid program that met the needs of the spec except that there were too few retreived chunks. Also, the retrieved chunks for queries that were referenced across multiple sources were not relevant. 
- *What I changed or overrode:*
I reviewed the printed outputs and noticed two main themes: CU Independent Articles returned 0 chunks and overall only 39 chunks were returned. I asked whether the problem was chunk size or source count and identified it was likely due to blocked pages. I increased the source document group and this brought the number up to 95 chunks which greatly improved the retrieval results. 

**Instance 2**

- *What I gave the AI:*
I gave the AI a series of evaluation questions to inspect the accuracy of the retreival. Eval questions and expected responses were included in the spec sheet based on what was discovered in the source documents. One such question was "what ghost story is associated with Macky Auditorium?" While specific, the initial model found Macky in another article that was not relevant to the murder and susequent ghost story.

- *What it produced:*
The AI produced a response that was also narrative-based like the question prompted. However, the expected response about the murder was still missing.

- *What I changed or overrode:*
I pushed back on rewriting eval queries to match the corpus since it would defeat the purpose. This helped me see the braoder issue with the embed library and also identified the blocked source files. Replacing the embed library with multi-qa-mpnet-base-dot-v1 increased the accuracy of Q&A queries. Adding additional source articles improved the available keywords. I also updated the Varsity lake eval question from "What is the origin story of Varisty Lake?" to "Tell me about Varsity Lake" which uses natural language. 
