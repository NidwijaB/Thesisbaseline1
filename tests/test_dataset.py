"""
tests/test_dataset.py
---------------------
Checks that training examples are built the way the evaluation expects: same prompt string,
loss on the output only, an end token after the output, and truncation that never cuts the output.
A one-character-per-token stub stands in for the real tokenizer, so no model download is needed.
"""

from src.finetuning.dataset import IGNORE_INDEX, encode_example
from src.prompting import FOOTER, HEADER, PROMPT_TEMPLATE, build_prompt, first_line

EOS = 0


class CharTokenizer:
    eos_token_id = EOS

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": [ord(c) for c in text]}


def decode(ids):
    return "".join(chr(i) for i in ids)


def test_training_prompt_matches_inference_prompt():
    assert PROMPT_TEMPLATE.format(input="x = foo.", output="bar()") == build_prompt("x = foo.") + "bar()"


def test_retrieved_chunks_go_before_the_code():
    class Chunk:
        content = "def helper():\n    pass"
        file_path = "pkg/util.py"

    prompt = build_prompt("x = helper.", [Chunk()])
    assert prompt.startswith(HEADER) and prompt.endswith("x = helper." + FOOTER)
    assert "# --- retrieved from pkg/util.py ---" in prompt and "# def helper():" in prompt


def test_loss_is_on_output_and_end_token_only():
    ex = encode_example({"input": "x = foo.", "output": "bar()"}, CharTokenizer(), max_length=512)
    n_prompt = len(build_prompt("x = foo."))
    assert ex["labels"][:n_prompt] == [IGNORE_INDEX] * n_prompt
    assert decode(ex["labels"][n_prompt:-1]) == "bar()"
    assert ex["labels"][-1] == EOS
    assert ex["input_ids"][-1] == EOS
    assert len(ex["input_ids"]) == len(ex["labels"]) == len(ex["attention_mask"])


def test_long_input_is_cut_from_the_left_and_output_survives():
    long_input = "".join(f"line{i}\n" for i in range(200)) + "x = foo."
    ex = encode_example({"input": long_input, "output": "bar()"}, CharTokenizer(), max_length=200)
    assert len(ex["input_ids"]) <= 200
    text = decode(ex["input_ids"][:-1])
    assert text.startswith(HEADER)                      # instruction kept
    assert text.endswith("x = foo." + FOOTER + "bar()")  # text nearest the cursor and the output kept
    assert ex["labels"][-1] == EOS


def test_overlong_output_is_truncated_without_end_token():
    ex = encode_example({"input": "x = foo.", "output": "y" * 500}, CharTokenizer(), max_length=100)
    assert len(ex["input_ids"]) <= 100
    assert ex["labels"][-1] != EOS


def test_first_line():
    assert first_line("a(b)\nnext") == "a(b)"
    assert first_line("only") == "only"
