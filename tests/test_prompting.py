from types import SimpleNamespace

import pytest

from src.prompting import (BASE_PROMPTS, HEADER, build_plain_prompt, build_prompt, build_system_prompt,
                           format_context)

CODE = "import os\n\ndef f(cfg):\n    return cfg."


def _chunk(path, text):
    return SimpleNamespace(file_path=path, content=text)


CHUNKS = [_chunk("a/util.py", "def helper():\n    pass"), _chunk("b/main.py", "x = 1")]


def test_plain_prompt_has_no_instruction_wrapper_and_ends_at_the_cursor():
    prompt = build_plain_prompt(CODE)
    assert prompt == CODE
    assert "### Instruction" not in prompt and "### Response" not in prompt


def test_plain_prompt_puts_retrieved_chunks_before_the_code_as_comments():
    prompt = build_plain_prompt(CODE, CHUNKS)
    assert prompt.endswith(CODE)
    assert prompt.startswith("# --- retrieved from a/util.py ---")
    assert "### Instruction" not in prompt
    assert prompt.index("b/main.py") < prompt.index("import os")
    assert all(line.startswith("#") or not line for line in prompt[:prompt.index(CODE)].splitlines())
    assert prompt == format_context(CHUNKS) + CODE


def test_adapter_systems_always_get_the_instruction_format():
    for base_prompt in BASE_PROMPTS:
        assert build_system_prompt(CODE, None, True, base_prompt) == build_prompt(CODE)
        assert build_system_prompt(CODE, CHUNKS, True, base_prompt) == build_prompt(CODE, CHUNKS)
    assert build_prompt(CODE).startswith(HEADER)


def test_frozen_systems_follow_base_prompt_and_default_is_unchanged():
    assert build_system_prompt(CODE, CHUNKS, False) == build_prompt(CODE, CHUNKS)          # default = first pilot
    assert build_system_prompt(CODE, CHUNKS, False, "instruction") == build_prompt(CODE, CHUNKS)
    assert build_system_prompt(CODE, None, False, "plain") == CODE                         # base: no chunks
    assert build_system_prompt(CODE, CHUNKS, False, "plain") == build_plain_prompt(CODE, CHUNKS)  # RAG


def test_unknown_base_prompt_is_rejected():
    with pytest.raises(ValueError):
        build_system_prompt(CODE, None, False, "fewshot")
