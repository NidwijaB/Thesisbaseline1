from src.evaluation.analyze_predictions import analyse, boot_diff_paired


def _row(hit, em_by_system, relevant=True):
    row = {"relevant_files": ["a.py"] if relevant else [], "relevant_in_top_k": hit}
    for system, em in em_by_system.items():
        row[system] = {"exact_match": em, "edit_similarity": em}
    return row


def test_hit_vs_miss_groups_and_difference():
    # rag_only is right on every hit and wrong on every miss
    rows = [_row(True, {"base": 0.0, "rag_only": 1.0, "finetuning_only": 0.0, "hybrid": 1.0}) for _ in range(6)]
    rows += [_row(False, {"base": 0.0, "rag_only": 0.0, "finetuning_only": 0.0, "hybrid": 0.0}) for _ in range(4)]
    res = analyse(rows)
    g = res["hit_vs_miss"]["rag_only"]["exact_match"]
    assert g["hit"]["n"] == 6 and g["miss"]["n"] == 4
    assert g["hit"]["mean"] == 1.0 and g["miss"]["mean"] == 0.0
    assert g["hit_minus_miss"]["mean"] == 1.0 and g["hit_minus_miss"]["ci95"][0] > 0
    d = res["paired_differences"]["hybrid - finetuning_only"]["exact_match"]
    assert d["mean"] == 0.6


def test_examples_without_relevant_file_are_left_out_of_hit_miss_only():
    rows = [_row(True, {"base": 0.0, "rag_only": 1.0, "finetuning_only": 0.0, "hybrid": 1.0}),
            _row(False, {"base": 0.0, "rag_only": 0.0, "finetuning_only": 0.0, "hybrid": 0.0}, relevant=False)]
    res = analyse(rows)
    assert res["n_with_relevant_file"] == 1
    assert res["hit_vs_miss"]["rag_only"]["exact_match"]["miss"]["n"] == 0
    assert res["paired_differences"]["rag_only - base"]["exact_match"]["mean"] == 0.5


def test_paired_difference_of_equal_scores_is_zero():
    assert boot_diff_paired([1, 0, 1], [1, 0, 1])["mean"] == 0.0
