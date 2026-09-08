"""
src/finetuning/trainer.py
--------------------------
LoRA / QLoRA fine-tuning entry point using HuggingFace PEFT + Transformers.
"""

from __future__ import annotations
from pathlib import Path

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training

from src.finetuning.dataset import build_dataset
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_finetuning(config_path: str = "configs/config.yaml"):
    """
    Loads the base model, wraps it with LoRA/QLoRA adapters, trains on
    data/processed/train.jsonl, and saves the adapted model + tokenizer to
    finetuning.output_dir (default: experiments/finetuned_model/).
    All hyperparameters (epochs, batch size, LoRA rank, etc.) come from
    configs/config.yaml -> finetuning.* — edit that file, not this one.
    """
    cfg = load_config(config_path)
    ft = cfg.finetuning

    logger.info(f"Loading tokenizer: {ft.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(ft.base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    logger.info(f"Loading base model: {ft.base_model}")

    bnb_config = None
    if ft.method == "qlora":
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=getattr(ft, "bnb_4bit_use_double_quant", True),
        )
        logger.info("QLoRA: loading model in 4-bit NF4")

    model = AutoModelForCausalLM.from_pretrained(
        ft.base_model,
        trust_remote_code=True,
        quantization_config=bnb_config,
        device_map="auto",
    )

    if ft.method in ("lora", "qlora"):
        if ft.method == "qlora":
            model = prepare_model_for_kbit_training(model)
        if getattr(ft, "gradient_checkpointing", False):
            model.gradient_checkpointing_enable()
        lora_cfg = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=ft.lora_r,
            lora_alpha=ft.lora_alpha,
            lora_dropout=ft.lora_dropout,
            target_modules=list(ft.target_modules),
            bias="none",
        )
        model = get_peft_model(model, lora_cfg)
        model.print_trainable_parameters()

    # ── Dataset ───────────────────────────────────────────────────────────────
    dataset = build_dataset(
        train_path="data/processed/train.jsonl",
        val_path="data/processed/val.jsonl",
        tokenizer=tokenizer,
        max_length=ft.max_seq_length,
    )

    # ── Training Arguments ────────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=ft.output_dir,
        num_train_epochs=ft.epochs,
        per_device_train_batch_size=ft.batch_size,
        gradient_accumulation_steps=ft.gradient_accumulation_steps,
        learning_rate=ft.learning_rate,
        fp16=ft.fp16,
        gradient_checkpointing=getattr(ft, "gradient_checkpointing", False),
        evaluation_strategy="epoch" if "validation" in dataset else "no",
        save_strategy="epoch",
        logging_steps=50,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset.get("validation"),
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model, padding=True),
    )

    logger.info("Starting fine-tuning …")
    trainer.train()
    model.save_pretrained(ft.output_dir)
    tokenizer.save_pretrained(ft.output_dir)
    logger.info(f"Model saved to {ft.output_dir}")


if __name__ == "__main__":
    run_finetuning()

