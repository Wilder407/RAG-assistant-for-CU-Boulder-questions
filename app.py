"""
app.py — CU Boulder Unofficial Guide
Gradio interface wiring query.py to a browser UI.

Run:
    python app.py

Then open http://localhost:7860 in your browser.

All heavy objects (embedding model, ChromaDB collection, Groq client) are
initialised once at startup and reused across requests.
"""

import os

import gradio as gr
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb

from query import ask
from retrieve import MODEL_NAME, COLLECTION_NAME, PERSIST_DIR

# ---------------------------------------------------------------------------
# STARTUP — load everything once
# ---------------------------------------------------------------------------

load_dotenv()

print(f"Loading embedding model: {MODEL_NAME} ...")
_model = SentenceTransformer(MODEL_NAME)

print(f"Connecting to ChromaDB at: {PERSIST_DIR} ...")
_chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
_collection    = _chroma_client.get_collection(COLLECTION_NAME)
print(f"  {_collection.count()} chunks ready.")

print("Initialising Groq client ...")
_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
print("  Ready.\n")

# ---------------------------------------------------------------------------
# HANDLER
# ---------------------------------------------------------------------------

def handle_query(question: str):
    """
    Called by Gradio on every button click or Enter keypress.
    Returns (answer, sources) tuple to fill the two output boxes.
    """
    if not question.strip():
        return "Please enter a question.", ""

    result = ask(
        question,
        model=_model,
        collection=_collection,
        groq_client=_groq,
    )

    source_items = []
    for s in result["sources"]:
        if " — " in s:
            place, url = s.split(" — ", 1)
            source_items.append(f'<a href="{url}" target="_blank" rel="noopener noreferrer">• {place}</a>')
        else:
            source_items.append(f'<span>• {s}</span>')
    label = '<p style="font-family: Playfair Display, serif; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #6b5e3e; margin-bottom: 0.4rem;">Retrieved from</p>'
    body = "<br>".join(source_items) if source_items else "<em>No sources retrieved.</em>"
    return result["answer"], label + body


# ---------------------------------------------------------------------------
# EXAMPLE QUESTIONS (shown below the input box)
# ---------------------------------------------------------------------------

EXAMPLES = [
    "What is the history behind the Dalton Trumbo Fountain?",
    "Was there a murder in Macky Auditorium?",
    "What wildlife can you spot on campus?",
    "What are some lesser-known study spots that aren't Norlin Library?",
    "Tell me about Varsity Lake.",
]

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;1,8..60,300&display=swap');

:root {
    --cu-gold:    #CFB87C;
    --cu-black:   #1a1a1a;
    --cu-stone:   #f5f0e8;
    --cu-warm:    #e8dfc8;
    --cu-rust:    #8B3A2A;
    --cu-ink:     #2c2416;
    --radius:     6px;
}

body, .gradio-container {
    background-color: var(--cu-stone) !important;
    font-family: 'Source Serif 4', Georgia, serif !important;
    color: var(--cu-ink) !important;
}

/* Header */
#header {
    text-align: center;
    padding: 2rem 1rem 1rem;
    border-bottom: 2px solid var(--cu-gold);
    margin-bottom: 1.5rem;
}
#header h1 {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: var(--cu-black);
    letter-spacing: -0.01em;
    margin: 0 0 0.25rem;
}
#header p {
    font-family: 'Source Serif 4', serif;
    font-style: italic;
    font-size: 1rem;
    color: #6b5e3e;
    margin: 0;
}

/* Input box */
#question-box textarea {
    background: #fff !important;
    border: 1.5px solid #c9bfa0 !important;
    border-radius: var(--radius) !important;
    font-family: 'Source Serif 4', serif !important;
    font-size: 1rem !important;
    color: var(--cu-ink) !important;
    padding: 0.75rem !important;
}
#question-box textarea:focus {
    border-color: var(--cu-gold) !important;
    box-shadow: 0 0 0 3px rgba(207,184,124,0.2) !important;
}
#question-box label {
    font-family: 'Playfair Display', serif !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: #6b5e3e !important;
}

/* Ask button */
#ask-btn {
    background: var(--cu-black) !important;
    color: var(--cu-gold) !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-family: 'Playfair Display', serif !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 0.65rem 2rem !important;
    transition: background 0.2s, color 0.2s !important;
    cursor: pointer !important;
}
#ask-btn:hover {
    background: var(--cu-gold) !important;
    color: var(--cu-black) !important;
}

/* Answer box */
#answer-box textarea {
    background: #fff !important;
    border: 1.5px solid #c9bfa0 !important;
    border-radius: var(--radius) !important;
    font-family: 'Source Serif 4', serif !important;
    font-size: 1rem !important;
    line-height: 1.7 !important;
    color: var(--cu-ink) !important;
    padding: 0.75rem !important;
}
#answer-box label {
    font-family: 'Playfair Display', serif !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: #6b5e3e !important;
}

/* Sources box */
#sources-box > div {
    background: var(--cu-warm) !important;
    border: 1.5px solid #c9bfa0 !important;
    border-radius: var(--radius) !important;
    font-family: 'Source Serif 4', serif !important;
    font-size: 0.88rem !important;
    color: #4a3f28 !important;
    padding: 0.75rem !important;
}
#sources-box a {
    display: block;
    color: #8B3A2A !important;
    text-decoration: underline;
    text-underline-offset: 3px;
    font-size: 0.88rem;
    margin-bottom: 0.2rem;
    word-break: break-all;
}
#sources-box a:hover {
    color: #1a1a1a !important;
}
#sources-box .label-wrap {
    font-family: 'Playfair Display', serif !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: #6b5e3e !important;
}

/* Examples */
.gr-examples {
    margin-top: 0.5rem !important;
}
.gr-examples button {
    font-family: 'Source Serif 4', serif !important;
    font-style: italic !important;
    font-size: 0.9rem !important;
    color: var(--cu-rust) !important;
    background: transparent !important;
    border: 1px solid #c9bfa0 !important;
    border-radius: var(--radius) !important;
    padding: 0.3rem 0.75rem !important;
    transition: background 0.15s !important;
}
.gr-examples button:hover {
    background: var(--cu-warm) !important;
}

/* Footer */
#footer {
    text-align: center;
    padding: 1rem;
    margin-top: 1.5rem;
    border-top: 1px solid #c9bfa0;
    font-size: 0.8rem;
    font-style: italic;
    color: #8a7a5a;
}
"""

with gr.Blocks(css=CSS, title="Beyond the Brochure") as demo:

    gr.HTML("""
        <div id="header">
            <h1>Beyond the Brochure</h1>
            <p>Hidden history, folklore, and campus secrets — things they don't tell you on the tour</p>
        </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):
            question_box = gr.Textbox(
                label="Your Question",
                placeholder="Ask about campus secrets, history, study spots, folklore…",
                lines=2,
                elem_id="question-box",
            )
            ask_btn = gr.Button("Ask the Guide", elem_id="ask-btn")

            gr.Examples(
                examples=EXAMPLES,
                inputs=question_box,
                label="Try one of these",
            )

        with gr.Column(scale=4):
            answer_box = gr.Textbox(
                label="Answer",
                lines=8,
                interactive=False,
                elem_id="answer-box",
            )
            sources_box = gr.HTML(
                value='<p style="font-family: Playfair Display, serif; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #6b5e3e;">Retrieved from</p>',
                elem_id="sources-box",
            )

    gr.HTML("""
        <div id="footer">
            Answers are grounded in retrieved sources only — always verify with the linked URLs.
        </div>
    """)

    # Wire up interactions
    ask_btn.click(
        fn=handle_query,
        inputs=question_box,
        outputs=[answer_box, sources_box],
    )
    question_box.submit(
        fn=handle_query,
        inputs=question_box,
        outputs=[answer_box, sources_box],
    )

if __name__ == "__main__":
    demo.launch()