from src.evaluation.forgetting_check import cut_completion, run_program


def test_completion_is_cut_at_first_top_level_statement():
    text = "    return a + b\n\n\ndef helper():\n    pass\nprint(1)"
    assert cut_completion(text).rstrip() == "    return a + b"


def test_run_program_pass_fail_and_timeout():
    assert run_program("assert 1 + 1 == 2")
    assert not run_program("assert 1 == 2")
    assert not run_program("while True:\n    pass", timeout=1)
