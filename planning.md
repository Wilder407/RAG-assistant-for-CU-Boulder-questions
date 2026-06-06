# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
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

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | CU Independent Newsletter| Article |https://cuindependent.com/2007/01/28/history-behind-the-name-cus-famous-monikers/ |
| 2 | HerCampus| Article | https://www.hercampus.com/school/cu-boulder/hidden-gems-to-study-at-cu-boulder/ |
| 3 | AboutBoulder | Article |https://aboutboulder.com/blog/exploring-the-hidden-gems-university-of-colorados-top-off-the-beaten-path-attractions/ |
| 4 | Cu Boulder Student Life | Website with Links| https://www.colorado.edu/today/2020/01/30/your-guide-campus-venues-museums-and-more |
| 5 | Visit Boulder | List and Map |  https://www.bouldercoloradousa.com/things-to-do/visiting-cu/things-to-do-at-cu/ |
| 6 | Coloradan Alumni Magazine | Website | https://colorado.edu/coloradan/2021/01/21/10-plants-and-animals-spot-campus |
| 7 | Cu Independent |Article | https://www.cuindependent.com/2013/10/24/secret-tunnels-and-murder-the-not-so-scary-truth/|
| 8 | Coloradan Alumni Magazine | Article |https://www.colorado.edu/coloradan/2010/09/01/unlocking-cu-secrets |
| 9 | BASIN | Text | https://bcn.boulder.co.us/basin/watershed/geology/historic.html
| 10 | CU Independent | Newspaper | https://www.cuindependent.com/2023/10/31/a-haunted-history-of-cus-macky-auditorium/ |
| 11 | About Boulder | Website | https://aboutboulder.com/blog/old-main-at-cu-boulder-history-flatirons-views-fun-facts/ |
| 12 | Reddit | Forum Thread | https://www.reddit.com/r/whatisit/comments/1rwtvbg/comment/ob2cvjy/ |
| 13 | Reddit | Forum Thread | https://www.reddit.com/r/cuboulder/comments/w0ylxm/what_are_some_good_hidden_places_or_resource/ |
| 14 |  Reddit | Forum Thread | https://www.reddit.com/r/whatisit/comments/1rwtvbg/comment/ob2cvjy/ |
| 15 |  Reddit | Forum Thread | https://www.reddit.com/r/cuboulder/comments/1stfz3m/whats_a_free_thing_to_do_in_boulder_that_most_cu/ |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

     For newspaper articles and webpages, I will use a chunk size of 300 tokens with a 
     75 token overlap. These documents are typically written about one subject matter. 
     At roughly 350 tokens, this chunk size should be sufficient to capture the full 
     context of the idea without pulling in unrelated information. The 75 token overaly
     ensures that sentences straddling a boundary remain retrievable from either end. 

     For Reddit comments and short student written posts, I will use a chunk size of 
     150 tokens with a 30 token overlap. These documents are already compact and 
     conversational. This size Larger chunk sizes would group together unrelated ideas. 

     For map captions and one-line entries, I will keep the input as one caption with no 
     splitting, usually 30 -80 tokens. These inputs typically have contain the full meaning.
     Instead of overlap, I will attach structured metadata such as location, source URL, 
     category) so retrieval has enough to surface them correctly.

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
