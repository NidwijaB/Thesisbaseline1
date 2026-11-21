from types import SimpleNamespace

from rank_bm25 import BM25Okapi

from experiments.run_comparison import add_noise, bm25_search, bm25_tokens
from src.prompting import truncate_code_left


class WordTokenizer:
    """Stand-in tokenizer: one token per whitespace-separated word."""

    def __call__(self, text, add_special_tokens=False):
        return SimpleNamespace(input_ids=text.split())

    def decode(self, ids):
        return " ".join(ids)


def _chunk(path, text):
    return SimpleNamespace(file_path=path, content=text, metadata={"split": "base"})


def _store(chunks):
    return SimpleNamespace(_chunks=chunks)


def test_bm25_ranks_the_chunk_sharing_identifiers_first_and_keeps_all_chunks():
    chunks = [_chunk("a.py", "def load_config(path): return yaml.safe_load(path)"),
              _chunk("b.py", "class Matrix: pass"),
              _chunk("c.py", "import os")]
    store = _store(chunks)
    bm25 = BM25Okapi([bm25_tokens(c.content) for c in chunks])
    ranked = bm25_search(store, bm25, "cfg = load_config(path)")
    assert [c.file_path for c in ranked][0] == "a.py"
    assert sorted(c.file_path for c in ranked) == ["a.py", "b.py", "c.py"]


def test_noise_chunks_come_from_other_repos_and_are_repeatable():
    stores = {f"{r}/main": _store([_chunk(f"{r}.py", f"text of {r}")]) for r in ("r1", "r2", "r3")}
    real = [_chunk("real.py", "real")]
    first = add_noise(real, 3, "r1", "task-1", ["r1", "r2", "r3"], "main", stores)
    again = add_noise(real, 3, "r1", "task-1", ["r1", "r2", "r3"], "main", stores)
    assert len(first) == 4
    assert [c.file_path for c in first] == [c.file_path for c in again]
    noise = [c for c in first if c.file_path.startswith("[noise from")]
    assert len(noise) == 3 and not any("r1" in c.file_path.split("]")[0] for c in noise)
    assert [c for c in first if c.file_path == "real.py"] == real


def test_truncate_code_left_keeps_the_text_nearest_the_cursor():
    tok = WordTokenizer()
    assert truncate_code_left("a b c d e", tok, 3) == "c d e"
    assert truncate_code_left("a b", tok, 3) == "a b"
    assert truncate_code_left("a b c d e", tok, None) == "a b c d e"


def test_new_relevant_ids_picks_test_examples_with_a_relevant_new_file():
    from experiments.run_comparison import new_relevant_ids

    def ex(tid, repo, target, snippet_files):
        return {"metadata": {"task_id": tid, "repository": repo, "file": target},
                "crossfile_context_retrieval": {"list": [{"filename": f} for f in snippet_files]}}

    manifest = {("r", "t1.py"): "test", ("r", "t2.py"): "test", ("r", "t3.py"): "test",
                ("r", "n.py"): "new", ("r", "b.py"): "base", ("other", "n.py"): "base"}
    split = {"e1": "test", "e2": "test", "e3": "test", "e4": "base"}
    rows = [ex("e1", "r", "t1.py", ["n.py", "b.py"]),    # relevant NEW file -> selected
            ex("e2", "r", "t2.py", ["b.py"]),            # only BASE files -> not selected
            ex("e3", "r", "t3.py", ["t3.py"]),           # own file is excluded -> not selected
            ex("e4", "r", "n.py", ["n.py"])]             # not a TEST example -> not selected
    assert new_relevant_ids(rows, manifest, split) == {"e1"}
    # a NEW file in a different repository does not count
    assert new_relevant_ids([ex("e1", "other", "t1.py", ["n.py"])], manifest, split) == set()
