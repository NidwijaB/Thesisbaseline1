"""
src/prompting.py
-----------------
The single prompt format used by training, the demo, the hybrid pipeline and the
evaluation. Keeping it in one place is what makes the three systems comparable:

  System A (RAG)     base model, prompt = build_prompt(code, retrieved chunks)
  System B (FT)      adapter,    prompt = build_prompt(code)
  System C (hybrid)  adapter,    prompt = build_prompt(code, retrieved chunks)

Training examples use exactly build_prompt(input) followed by the output (see
src/finetuning/dataset.py), so B sees at inference what it saw in training. C and A
add retrieved chunks, which the adapter has not seen in training (the RAFT-style
variant that would train on retrieval-formatted prompts is not built yet).

No torch import here, so the corpus builders and tests can use it.
"""

from __future__ import annotations

HEADER = "### Instruction:\nComplete the following code.\n\n### Input:\n"
FOOTER = "\n\n### Response:\n"
# Same as the string used since the first training run: HEADER + {input} + FOOTER + {output}
PROMPT_TEMPLATE = HEADER + "{input}" + FOOTER + "{output}"

QUERY_LINES = 20         # retrieval query = last lines of the code, as in the index sanity check
MAX_CHUNK_CHARS = 1200   # keep the prompt small; chunks are up to 256 lines


def format_context(chunks: list | None) -> str:
    """Retrieved chunks as comment lines, nearest first, placed before the code."""
    if not chunks:
        return ""
    parts = []
    for chunk in chunks:
        body = "\n".join("# " + line for line in chunk.content[:MAX_CHUNK_CHARS].splitlines())
        parts.append(f"# --- retrieved from {chunk.file_path} ---\n{body}")
    return "\n".join(parts) + "\n\n"


def build_prompt(code: str, chunks: list | None = None) -> str:
    """Prompt that ends right where the model should start writing."""
    return HEADER + format_context(chunks) + code + FOOTER


def retrieval_query(code: str) -> str:
    return "\n".join(code.split("\n")[-QUERY_LINES:])


def first_line(text: str) -> str:
    """Completions are scored on the first line only (the benchmarks ask for one line)."""
    return text.split("\n")[0]
