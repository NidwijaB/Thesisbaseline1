# Hybrid RAG + Fine-Tuning Framework for Repository-Level Code Completion

## Overview

This repository implements and evaluates a **Hybrid Retrieval-Augmented Generation (RAG) and Fine-Tuned Language Model framework** for repository-level code completion in enterprise-style software projects.

The project investigates whether combining:

- Repository-aware retrieval mechanisms
- Project-adapted code language models

can outperform standalone approaches for code completion tasks requiring:

- Cross-file dependencies
- Internal API usage
- Project-specific coding patterns
- Repository-level context

The research compares three approaches:

1. **RAG-Only Baseline**
2. **Fine-Tuning-Only Baseline**
3. **Hybrid RAG + Fine-Tuning Model (Proposed System)**

---

# Research Motivation

Modern code completion models perform well on general programming tasks but often struggle in enterprise repositories where completions depend on:

- Internal APIs
- Cross-file references
- Shared utility modules
- Domain-specific naming conventions
- Repository architecture

Repository-level benchmarks such as:

- RepoBench
- CrossCodeEval

demonstrate that multi-file code completion remains challenging even for state-of-the-art code models.

This project aims to bridge that gap by combining retrieval-based context augmentation with project-specific model adaptation.

---

# Research Objectives

The project aims to:

1. Compare RAG-only, Fine-Tuning-only, and Hybrid systems.
2. Measure the impact of repository context on code completion quality.
3. Evaluate retrieval effectiveness for repository-level tasks.
4. Assess trade-offs between accuracy, latency, and resource usage.
5. Provide practical recommendations for enterprise code completion systems.

---

# System Architecture

## Baseline 1: RAG-Only

```text
Repository
    ↓
Code Chunking
    ↓
Embeddings
    ↓
Vector Database
    ↓
Retriever
    ↓
LLM
    ↓
Code Completion
```

### Workflow

1. Index repository files.
2. Generate embeddings for code chunks.
3. Store embeddings in vector database.
4. Retrieve relevant snippets for a completion task.
5. Append retrieved context to the prompt.
6. Generate completion using a code LLM.

---

## Baseline 2: Fine-Tuning Only

```text
Repository Examples
        ↓
Training Pair Creation
        ↓
Fine-Tuning Dataset
        ↓
Code Model Fine-Tuning
        ↓
Project-Adapted Model
        ↓
Code Completion
```

### Workflow

1. Extract completion examples.
2. Create input-output training pairs.
3. Fine-tune a base coding model.
4. Perform completion without retrieval.

Example:

Input:

```python
def process_user():
```

Output:

```python
user = UserFactory.create()
validate_user(user)
return user
```

---

## Proposed System: Hybrid RAG + Fine-Tuning

```text
Repository
      ↓
Retriever
      ↓
Relevant Code Context
      ↓
Fine-Tuned Model
      ↓
Repository-Aware Completion
```

### Workflow

1. User writes partial code.
2. Retriever searches repository.
3. Relevant files/snippets are retrieved.
4. Retrieved context is injected into prompt.
5. Fine-tuned model generates completion.

This combines:

- Dynamic repository knowledge from RAG
- Project adaptation from fine-tuning

---

# Project Structure

```text
project-root/
│
├── data/
│   ├── repobench/
│   ├── crosscodeeval/
│   ├── processed/
│   └── embeddings/
│
├── src/
│   ├── preprocessing/
│   ├── retrieval/
│   ├── finetuning/
│   ├── hybrid/
│   ├── evaluation/
│   └── utils/
│
├── configs/
│
├── experiments/
│
├── notebooks/
│
├── results/
│
├── docs/
│
├── tests/
│
└── README.md
```

---

# Phase 1: Literature Review and Problem Analysis

Key topics:

- Repository-level code completion
- Retrieval-Augmented Generation (RAG)
- Fine-tuning of code language models
- Internal API reasoning
- Enterprise code intelligence

Relevant research includes:

- RepoBench
- CrossCodeEval
- RepoCoder
- RAFT
- RAG vs Fine-Tuning studies
- Internal API inference techniques

---

# Phase 2: Dataset Preparation

## Datasets

### RepoBench

Provides:

- Complete repositories
- Multiple source files
- Repository-level completion tasks
- Retrieval benchmarks

### CrossCodeEval

Provides:

- Cross-file dependencies
- Repository context
- Completion targets
- Multilingual code examples

---

## Preprocessing Tasks

### Repository Parsing

Extract:

- File structure
- Import relationships
- Function definitions
- Class definitions

### Task Generation

Example:

Input:

```python
def get_customer():
```

Ground Truth:

```python
customer = InternalCustomerFactory()
return customer
```

### Metadata Extraction

Store:

- Repository ID
- File path
- Language
- Function boundaries
- Dependency information

### Context Construction

Link:

- Imports
- API usage
- Call graphs
- Related files

---

# Phase 3: RAG Baseline Implementation

## Technology Stack

### Embedding Models

Possible options:

- CodeBERT
- UniXCoder
- bge-code
- Instructor embeddings

### Vector Database

Choose one:

- FAISS
- ChromaDB

### LLMs

Candidate models:

- CodeT5+
- StarCoder2
- Qwen2.5-Coder
- DeepSeek-Coder

---

## Retrieval Pipeline

```text
Repository Files
      ↓
Chunking
      ↓
Embeddings
      ↓
Vector Store
      ↓
Similarity Search
      ↓
Context Retrieval
```

---

## Prompt Format

Example:

```text
Current File:

def get_customer():

Retrieved Context:

FileA.py
------------
class InternalCustomerFactory:
    ...

FileB.py
------------
factory = InternalCustomerFactory()

Task:
Complete the code.
```

---

# Phase 4: Fine-Tuning Baseline

## Objective

Adapt a foundation code model to repository-specific completion patterns.

---

## Training Dataset Format

Example:

```json
{
  "input": "def process_user():",
  "output": "user = UserFactory.create()\nreturn user"
}
```

---

## Candidate Models

### Encoder-Decoder

- CodeT5+

### Decoder-Only

- StarCoder2
- DeepSeek-Coder
- Qwen2.5-Coder

---

## Fine-Tuning Approaches

### Full Fine-Tuning

Update all model parameters.

### Parameter-Efficient Fine-Tuning (Preferred)

- LoRA
- QLoRA

Benefits:

- Lower GPU usage
- Faster experimentation
- Better scalability

---

# Phase 5: Hybrid RAG + Fine-Tuning

## Core Research Contribution

The hybrid system combines:

### Retrieval Strengths

- Dynamic context access
- Cross-file awareness
- Internal API discovery

### Fine-Tuning Strengths

- Repository adaptation
- Naming convention learning
- Coding style learning

---

## Hybrid Workflow

```text
User Query
     ↓
Retriever
     ↓
Top-K Relevant Snippets
     ↓
Prompt Augmentation
     ↓
Fine-Tuned Model
     ↓
Code Completion
```

---

## Research Questions

### RQ1

Does repository retrieval improve completion accuracy compared to standalone fine-tuning?

### RQ2

Does fine-tuning improve the usefulness of retrieved context?

### RQ3

Does the hybrid approach outperform individual baselines?

### RQ4

What retrieval strategies best support enterprise repository completion?

---

# Phase 6: Evaluation

## Evaluation Setup

All three systems will be evaluated on the same benchmark tasks:

1. RAG Only
2. Fine-Tuning Only
3. Hybrid RAG + Fine-Tuning

---

## Primary Metrics

### Exact Match (EM)

Measures:

```text
Prediction == Ground Truth
```

Higher is better.

---

### Edit Similarity

Measures similarity between:

- Predicted code
- Reference completion

Possible metrics:

- Levenshtein similarity
- CodeBLEU

---

### Identifier Accuracy

Measures correctness of:

- Function names
- Class names
- Variable names
- Internal API usage

This is especially important for enterprise repositories.

---

### Retrieval Quality

#### Precision@K

```text
Relevant Retrieved Items
------------------------
Total Retrieved Items
```

#### Recall@K

```text
Relevant Retrieved Items
------------------------
Total Relevant Items
```

Questions:

- Did retrieval return useful files?
- Were supporting APIs retrieved?

---

### Efficiency Metrics

#### Latency

Measure:

- Retrieval time
- Inference time
- End-to-end completion time

#### Resource Usage

Measure:

- GPU utilization
- CPU utilization
- Memory consumption

---

# Experimental Tracking

For every experiment, log:

- Model version
- Dataset version
- Retrieval configuration
- Embedding model
- Chunk size
- Top-K value
- Latency
- Evaluation metrics

Suggested tools:

- MLflow
- Weights & Biases
- TensorBoard

---

# Expected Outcomes

The project expects to determine:

1. Whether RAG is superior to fine-tuning for repository-level completion.
2. Whether hybrid adaptation provides additional gains.
3. Which retrieval strategy best supports cross-file completion.
4. Trade-offs between accuracy and efficiency.
5. Recommendations for enterprise deployment scenarios.

---

# Future Extensions

Potential future work:

- Graph-based repository retrieval
- Dependency-aware retrieval
- AST-based indexing
- Internal API knowledge graphs
- Agentic repository navigation
- Multi-repository adaptation
- IDE integration (VS Code Extension)

---

# References

Primary research foundations:

- RepoBench
- CrossCodeEval
- RepoCoder
- RAFT
- RAG vs Fine-Tuning comparative studies
- Internal API Inference for Project-Specific Completion

See `/docs/references.md` for the complete bibliography.