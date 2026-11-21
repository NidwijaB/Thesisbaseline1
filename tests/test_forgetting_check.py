from src.evaluation.forgetting_check import cut_completion, run_program


def test_completion_is_cut_at_first_top_level_statement():
    text = "    return a + b\n\n\ndef helper():\n    pass\nprint(1)"
    assert cut_completion(text).rstrip() == "    return a + b"


def test_run_program_pass_fail_and_timeout():
    assert run_program("assert 1 + 1 == 2")
    assert not run_program("assert 1 == 2")
    assert not run_program("while True:\n    pass", timeout=1)


def test_humaneval_prompt_modes_and_zero_base_guard():
    import pytest
    from src.evaluation.forgetting_check import build_humaneval_prompt, relative_change
    stub = 'def add(a, b):\n    """Add."""\n'
    assert build_humaneval_prompt(stub, "plain") == stub
    wrapped = build_humaneval_prompt(stub, "instruction")
    assert "### Instruction" in wrapped and stub in wrapped
    with pytest.raises(ValueError):
        build_humaneval_prompt(stub, "other")
    assert relative_change(0.0, 0.25) is None            # base 0: undefined, never a division error
    assert relative_change(0.4, 0.3) == -0.25
