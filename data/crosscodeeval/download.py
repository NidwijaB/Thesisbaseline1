"""
data/crosscodeeval/download.py
--------------------------------
Downloads CrossCodeEval (Python) and saves it locally.

IMPORTANT — two ways to get this dataset, pick ONE:

1. Official release (amazon-science/cceval on GitHub)
   The authors distribute the real benchmark as a `.tar.xz` archive that is
   NOT on the HuggingFace Hub — you have to request/download it manually:
       https://github.com/amazon-science/cceval
   After downloading `crosscodeeval_data.tar.xz`, extract it into this folder:
       tar -xvJf crosscodeeval_data.tar.xz -C data/crosscodeeval/
   If you go this route, IGNORE the code below and just extract the archive —
   then update `src/preprocessing/prepare_datasets.py` to read the extracted
   .jsonl files directly (field names are documented in the repo's README:
   prompt / groundtruth / crossfile_context).

2. Community HuggingFace mirror (used by default below — faster, no email
   needed, good enough for a thesis baseline)
       https://huggingface.co/datasets/ZHENGRAN/cross_code_eval_python
   Field names differ slightly from the official release (see comments in
   prepare_datasets.py) — this script + the preprocessing script already
   handle that mapping for you.

Run once:
    python data/crosscodeeval/download.py
"""

from __future__ import annotations
from pathlib import Path
from datasets import load_dataset

DATASET_ID = "ZHENGRAN/cross_code_eval_python"
OUTPUT_DIR = Path(__file__).parent  # data/crosscodeeval/


def download():
    print(f"Downloading CrossCodeEval (community mirror): {DATASET_ID} ...")
    dataset = load_dataset(DATASET_ID, "default")
    dest = OUTPUT_DIR / "python"
    dataset.save_to_disk(str(dest))
    print(f"  -> saved to {dest}")
    print("CrossCodeEval download complete.")
    print("Next step: run src/preprocessing/prepare_datasets.py")


if __name__ == "__main__":
    download()