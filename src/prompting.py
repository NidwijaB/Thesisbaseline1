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

Option added after the first pilot (progress log Entry 36): the frozen model (base, RAG) can be given a
plain continuation prompt instead (`build_plain_prompt`), because it does not follow the instruction
wrapper. The adapter systems (B, C) keep the training format either way.

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


def build_plain_prompt(code: str, chunks: list | None = None) -> str:
    """Plain continuation prompt, no instruction wrapper: retrieved chunks as comments (if any) then the
    code, ending right at the cursor so the model simply continues the line. This is how a model that was
    not fine-tuned on the instruction format is normally asked to complete code."""
    return format_context(chunks) + code


RAG_FORMATS = ("comments", "qwen_repo")


def build_repo_prompt(code: str, chunks: list | None, repo: str, target: str) -> str:
    """Repository-level prompt in the format Qwen2.5-Coder was trained for: the other files first, each behind a
    `<|file_sep|>` marker and path, then the file being completed ending right at the cursor. Used for the frozen RAG
    system with `--rag-format qwen_repo`; the comment-wrapped chunks of `build_plain_prompt` made the frozen model emit
    fill-in-the-middle tokens or stop at once (progress log Entry 42)."""
    parts = [f"<|repo_name|>{repo}"]
    for chunk in chunks or []:
        parts.append(f"<|file_sep|>{chunk.file_path}\n{chunk.content[:MAX_CHUNK_CHARS]}")
    parts.append(f"<|file_sep|>{target}\n{code}")
    return "\n".join(parts)


# How the models without the adapter (base, RAG) are prompted. "instruction" is the wrapper the adapter
# was trained on (the first pilot used it; the frozen model does not follow it, see progress log Entry 36);
# "plain" is a raw continuation. Models with the adapter always use the instruction format.
BASE_PROMPTS = ("instruction", "plain")


def build_system_prompt(code: str, chunks: list | None, uses_adapter: bool, base_prompt: str = "instruction",
                        rag_format: str = "comments", repo: str = "", target: str = "") -> str:
    """The prompt for one system. Adapter systems (B, C): instruction format. Frozen model (base, A):
    `base_prompt`. Retrieved chunks are passed in only for the systems that use retrieval. With
    base_prompt "plain" and rag_format "qwen_repo", the frozen RAG system gets the repository-level format
    (`build_repo_prompt`); the base model without chunks is unchanged."""
    if base_prompt not in BASE_PROMPTS:
        raise ValueError(f"base_prompt must be one of {BASE_PROMPTS}, got {base_prompt!r}")
    if rag_format not in RAG_FORMATS:
        raise ValueError(f"rag_format must be one of {RAG_FORMATS}, got {rag_format!r}")
    if uses_adapter or base_prompt == "instruction":
        return build_prompt(code, chunks)
    if rag_format == "qwen_repo" and chunks:
        return build_repo_prompt(code, chunks, repo, target)
    return build_plain_prompt(code, chunks)


def retrieval_query(code: str) -> str:
    return "\n".join(code.split("\n")[-QUERY_LINES:])


def first_line(text: str) -> str:
    """Completions are scored on the first line only (the benchmarks ask for one line)."""
    return text.split("\n")[0]


def truncate_code_left(code: str, tokenizer, max_tokens: int | None) -> str:
    """Keep the last `max_tokens` tokens of the code (the text nearest the cursor), as training did
    for over-long inputs. Retrieved chunks are not cut. None leaves the code unchanged."""
    if not max_tokens:
        return code
    ids = tokenizer(code, add_special_tokens=False).input_ids
    if len(ids) <= max_tokens:
        return code
    return tokenizer.decode(ids[-max_tokens:])
