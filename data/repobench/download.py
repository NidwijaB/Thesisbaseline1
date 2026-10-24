"""
data/repobench/download.py
---------------------------
Downloads RepoBench (Python, v1.1) from HuggingFace and saves it locally.

RepoBench provides repository-level code completion tasks with cross-file
context already attached — this is what makes it useful for evaluating
retrieval (RAG) quality, not just raw completion accuracy.

Dataset: https://huggingface.co/datasets/tianyang/repobench_python_v1.1
Splits (the dataset has one "default" config; these are splits, not configs):
    - "cross_file_first"  : next line depends on a cross-file symbol used
                             for the first time in the current file
    - "cross_file_random" : next line depends on a cross-file symbol used
                             elsewhere already (harder retrieval case)
    - "in_file"           : next line only needs in-file context (no
                             retrieval benefit expected — useful as a
                             control group)

Run once:
    python data/repobench/download.py
"""

from __future__ import annotations
from pathlib import Path
from datasets import load_dataset

# Configs to pull. cross_file_first + cross_file_random are the ones that
# actually exercise retrieval; in_file is kept as a control/ablation set.
CONFIGS = ["cross_file_first", "cross_file_random", "in_file"]

OUTPUT_DIR = Path(__file__).parent  # data/repobench/


def download():
    # The HF dataset has a single "default" config; the task settings are splits.
    print("Downloading RepoBench (all splits) ...")
    dataset = load_dataset("tianyang/repobench_python_v1.1")
    print(f"  available splits: {list(dataset.keys())}")

    for split_name in CONFIGS:
        if split_name not in dataset:
            print(f"  WARNING: split '{split_name}' not found, skipping")
            continue
        dest = OUTPUT_DIR / split_name
        dataset[split_name].save_to_disk(str(dest))
        print(f"  -> {split_name}: {len(dataset[split_name])} examples saved to {dest}")

    print("RepoBench download complete.")
    print("Next step: run src/preprocessing/prepare_datasets.py")


if __name__ == "__main__":
    download()