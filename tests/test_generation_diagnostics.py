from src.evaluation.inspect_raw import summarize


def test_classify_stop_reasons():
    from src.generation import classify_stop
    assert classify_stop([5, 6, 99], 99, 128, "ab") == "eos"                       # last token is end-of-text
    assert classify_stop([5, 6, 7], 99, 3, "abc") == "max_tokens"                  # hit the limit, no newline
    assert classify_stop([5, 6, 7], 99, 128, "abc\n") == "newline"                 # stop string reached
    assert classify_stop([5, 6, 7], 99, 3, "ab\n") == "newline"                    # limit reached but a newline was written
    assert classify_stop([], 99, 128, "") == "newline"
    assert classify_stop([1, 2], None, 128, "x") == "newline"                      # no eos id known


def _row(task_id, prediction, stop, n):
    cell = {"prediction": prediction, "raw": prediction + "<|endoftext|>", "n_new_tokens": n, "stop_reason": stop}
    return {"task_id": task_id, "reference": "ref", "base": dict(cell, prediction="x = 1", stop_reason="newline"),
            "rag_only": cell}


def test_summarize_counts_stop_reasons_and_short_answers():
    rows = [_row("a", "", "eos", 1), _row("b", "und", "eos", 2), _row("c", "plot(x)", "newline", 4)]
    s = summarize(rows)
    assert s["rag_only"]["stop_reasons"] == {"eos": 2, "newline": 1}
    assert s["rag_only"]["empty_or_short"] == 2          # "" and "und" (under 5 characters)
    assert s["base"]["empty_or_short"] == 0
    assert [t[0] for t in s["rag_only"]["short_examples"]] == ["a", "b"]
    assert summarize([{"task_id": "z", "reference": "r", "base": {"prediction": "x"}}]) == {}   # no diagnostics saved
