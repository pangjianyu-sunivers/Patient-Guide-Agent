# ChatZOC Hotline — Intelligent Ophthalmology Customer-Service Agent

A Flask-based intelligent hotline service for **Zhongshan Ophthalmic Center (ZOC), Sun Yat-sen University**.
It combines a local **Retrieval-Augmented Generation (RAG)** pipeline — built on ChromaDB + a sentence-embedding model — with the in-house **ChatZOC** large language model to answer patient phone-call questions about registration, triage, medical-insurance fees, disease consultation, surgery scheduling, and more.

---

## Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Architecture Overview](#architecture-overview)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Running the Service](#running-the-service)
7. [API Usage](#api-usage)
8. [Knowledge Base Format](#knowledge-base-format)
9. [Intent Categories](#intent-categories)
10. [Working-Hours Logic](#working-hours-logic)
11. [Logging](#logging)
12. [Notes & Limitations](#notes--limitations)

---

## Features

- **Multi-turn dialogue** with in-memory per-session history.
- **Intent classification** into 7 ophthalmology-oriented categories via the LLM.
- **Query rewriting** — pronouns and missing subjects in follow-up questions are completed using dialogue history before retrieval.
- **RAG retrieval** with ChromaDB + SentenceTransformer embeddings, filtered by intent-specific knowledge-base partitions.
- **Rule-based short-circuits** for greetings, idle prompts, repeat requests, hang-ups, and transfer-to-human requests.
- **Automatic human-agent fallback** that respects ZOC working hours and Chinese statutory holidays.
- **Phone-number redaction** — any number matching a standard pattern in the model output is replaced with the official hotline number.
- **Per-call structured logging** with latency breakdown for each pipeline stage (intent → rewrite → summarize → retrieve → answer).

---

## Project Structure

```
code_hotline/
├── BCE_embedding_model/
│   └── embedding_model_link.txt      # Download link for the embedding model
├── knowledge_base/
│   └── knowledge_base.json           # Q/A knowledge base (with `kb` partition tags)
├── phonecall_log_detail_time_check/  # Per-session call logs (auto-generated)
├── script/
│   └── script.py                     # Main Flask application
└── README.md
```

---

## Architecture Overview

```
         ┌──────────────────┐
  Caller │  POST /chat      │
   ─────▶│  {sid, message}  │
         └────────┬─────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │  Rule-based router   │  greet / idle / hangup / human / repeat
       └────────┬─────────────┘
                │ (fall-through)
                ▼
       ┌──────────────────────┐
       │  Intent classifier   │  LLM → one of 7 categories
       └────────┬─────────────┘
                ▼
       ┌──────────────────────┐
       │  Query rewriter      │  LLM completes missing subjects/pronouns
       └────────┬─────────────┘
                ▼
       ┌──────────────────────┐
       │  History summarizer  │  LLM merges dialogue context
       └────────┬─────────────┘
                ▼
       ┌──────────────────────┐
       │  ChromaDB retrieval  │  filtered by kb = intent partition
       └────────┬─────────────┘
                ▼
       ┌──────────────────────┐
       │  LLM answer          │  ChatZOC-V1 with few-shot + KB context
       └────────┬─────────────┘
                ▼
       ┌──────────────────────┐
       │  Post-processing     │  punctuation, phone redaction, 180-char cap
       └────────┬─────────────┘
                ▼
              JSON response
```

---

## Requirements

- Python 3.9+
- A reachable LLM HTTP endpoint (default in the code: `http://10.168.104.1:8095/chat`, model `ChatZOC-V1`).
- Python packages:

```bash
flask
chromadb
sentence-transformers
requests
```

You will also need the **BCE embedding model** weights placed in the folder `BCE_embedding_model/` (the code loads it via `SentenceTransformerEmbeddingFunction(model_name="BCE_embedding_model")`).
A reference download link is stored in `BCE_embedding_model/embedding_model_link.txt` (e.g. `https://huggingface.co/moka-ai/m3e-base/tree/main`).

---

## Installation

```bash
# 1. Clone / copy the project
cd code_hotline

# 2. (Recommended) Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install flask chromadb sentence-transformers requests

# 4. Download the embedding model into ./BCE_embedding_model/
#    so the folder directly contains config.json, pytorch_model.bin, etc.
```

---

## Running the Service

```bash
cd script
python script.py
```

On start-up the service will:

1. Create an in-memory Chroma collection `chatZOC`.
2. Load `knowledge_base/knowledge_base.json` and upsert every Q/A entry.
3. Print "Knowledge base successfully created".
4. Listen on **`0.0.0.0:8181`** for `POST /chat` requests.

---

## API Usage

### Endpoint

`POST http://<host>:8181/chat`

### Request body

```json
{
  "sid": "caller-session-id-001",
  "message": "我想咨询一下白内障手术怎么预约"
}
```

- `sid` — unique caller/session identifier. When it changes, dialogue history is reset automatically.
- `message` — the patient's utterance. A few reserved values trigger canned responses:

| `message`       | Behavior                                                                 |
| --------------- | ------------------------------------------------------------------------ |
| `answer`        | Returns the opening greeting and resets context.                         |
| `idle0/1/2`     | Returns a gentle re-prompt asking the caller to speak.                   |
| `noinputtimeout`| Same as `idle*`.                                                         |
| `hungup`        | Returns an empty response (call-end marker).                             |

### Response (debug format)

```json
[
  {
    "sid": "caller-session-id-001",
    "query_modified": "白内障手术怎么预约？",
    "prompt_after_summary": "白内障手术怎么预约？",
    "intend": "挂号流程问题",
    "text": "您好，您可以关注我院公众号…",
    "soft_text": "您好，您可以关注我院公众号…",
    "recipient_id": "123456",
    "utterance_id": "utter_1",
    "object_name": "greeting",
    "timestamp": 1590227722.11,
    "sys_state": "READY"
  }
]
```

> The code also prepares a slimmer production payload (`response_json`); switch the final `return` in `chat_with_chatZOC` if you only need the production shape.

### Transfer-to-human trigger

Utterances containing `转人工`, `人工服务`, or `接人工` trigger the human-handoff path. During business hours the reply carries the machine-readable tail `#####{"code":3000}` for the CTI layer to pick up.

---

## Knowledge Base Format

`knowledge_base/knowledge_base.json` is a dict-of-dicts with four parallel fields:

```json
{
  "no.":       { "0": 1, "1": 2, ... },
  "question":  { "0": "怎么挂号？", "1": "…", ... },
  "answer":    { "0": "您好，您可以…",  "1": "…", ... },
  "kb":        { "0": "guahaoliucheng", "1": "daozhenfenzhen", ... }
}
```

The `kb` field is used as a **ChromaDB metadata filter** so each intent retrieves only from its own partition.

Supported `kb` partitions:

| `kb` value          | Intent                            |
| ------------------- | --------------------------------- |
| `guahaoliucheng`    | Registration process              |
| `daozhenfenzhen`    | Guidance / triage                 |
| `yibaofeiyong`      | Medical insurance & fees          |
| `shoushuanpai`      | Surgery scheduling                |
| `qitawenti`         | Other questions                   |

`jibingzixun` (disease consultation) is answered by the LLM directly without RAG.

---

## Intent Categories

The intent classifier prompt (see `intend_find` in `script.py`) maps each utterance to one of:

1. 挂号流程问题 — Registration process
2. 导诊分诊问题 — Guidance / triage
3. 医保费用问题 — Medical insurance / fees
4. 疾病咨询问题 — Disease consultation
5. 手术安排 — Surgery scheduling
6. 礼貌用语 — Polite greetings / thanks
7. 其他问题 — Other

Each branch has its own pipeline (history summarization → KB retrieval → answer generation) tuned to the domain.

---

## Working-Hours Logic

`if_is_rest_time()` decides whether human service is available. Business hours are:

- **Morning:** 08:00 – 12:00
- **Afternoon:** 14:30 – 17:30
- **Weekdays only**, with explicit override lists for:
  - `special_workday` — Saturdays/Sundays that are treated as working days.
  - `special_restday` — weekdays treated as holidays (Chinese statutory holidays).

Both lists are hard-coded for **2026** and must be updated yearly.

---

## Logging

For every request, a log line is appended to:

```
phonecall_log_detail_time_check/<sid>.txt
```

Each record includes a UUID, timestamp, the input, the output, the classified intent, the rewritten/summarized prompt, the full dialogue history, and a **latency breakdown** for every pipeline stage:

- `time_spent_of_total_generation`
- `time_spent_of_intend_find`
- `time_spent_of_question_modify`
- `time_spent_of_history_sumary`
- `time_spent_of_find_knowledge`
- `time_spent_of_answer`

This makes it easy to profile bottlenecks in production.

---

## Notes & Limitations

- **Global state.** `history`, `prompt_after_summary`, and `query_modified` are module-level globals. They are reset per `sid`, but the server is not safe for concurrent multi-caller traffic as-is — wrap the state in a per-session store (e.g. Redis or a dict keyed by `sid`) before scaling.
- **Debug mode.** `app.run(..., debug=True)` is enabled; turn it off in production and serve behind a real WSGI server (e.g. `gunicorn`, `uwsgi`).
- **LLM endpoint.** The IP, port, model name, and API key in `send_to_llm` are environment-specific; move them to environment variables before deploying.
- **Response length.** Replies are hard-capped at 180 characters after generation, matching the TTS layer's comfortable utterance length.
- **Phone-number redaction** only catches the pattern `\d{3}[-\s]?\d{8}`. Adjust if your deployment uses different formats.
- **Holiday tables** in `if_is_rest_time()` must be updated every calendar year.

---

## License

Internal project — license to be specified by the maintainers of Zhongshan Ophthalmic Center.
