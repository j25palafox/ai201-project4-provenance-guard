# Provenance Guard

Provenance Guard is a backend attribution-analysis service for creative sharing platforms. It accepts text-based creative content, analyzes it using multiple signals, returns a confidence-scored attribution result, generates a reader-facing transparency label, and supports creator appeals when a classification is contested.

The goal is not to prove authorship with certainty or punish creators for using AI. The goal is to give platforms and readers clearer context while also giving creators a fair way to contest automated decisions.

---

## Features

Provenance Guard implements the required project features:

* Content submission endpoint for text attribution analysis
* Multi-signal detection pipeline using more than one signal
* Confidence scoring with uncertainty
* Reader-facing transparency labels
* Appeals workflow for contested classifications
* Rate limiting on API endpoints
* Structured audit logging for decisions and appeals

---

## Architecture Overview

The full architecture diagram is included in `planning.md` under the `## Architecture` section.

At a high level, a text submission moves through the system like this:

1. A creative platform sends submitted text to the Provenance Guard API.
2. The API validates the request and applies rate limiting.
3. The detection pipeline analyzes the text using multiple attribution signals.
4. The scoring engine combines those signals into an AI-likelihood score.
5. The classification layer converts that score into one of three results:

   * `likely_ai`
   * `likely_human`
   * `uncertain`
6. The label generator returns plain-language transparency text for readers.
7. The decision is saved to the content store and written to the audit log.
8. If the creator appeals, the appeal is saved, the submission status changes to `under_review`, and the appeal is also written to the audit log.

---

## API Endpoints

### `POST /submit`

Submits text for attribution analysis.

Example request:

```json
{
  "creator_id": "creator-001",
  "text": "Artificial intelligence represents a transformative paradigm shift in modern society..."
}
```

Example response:

```json
{
  "content_id": "generated-content-id",
  "creator_id": "creator-001",
  "result": "likely_ai",
  "confidence": 0.91,
  "label_type": "high_confidence_ai",
  "transparency_label": "Provenance Guard found strong signals that this text was likely generated or heavily shaped by AI. This label is based on automated analysis and may be appealed by the creator.",
  "signals": {
    "llm_signal": {
      "score": 0.94,
      "explanation": "The text uses broad, polished, generalized phrasing often associated with AI-generated writing."
    },
    "stylometric_signal": {
      "score": 0.78,
      "explanation": "The text has highly consistent sentence structure and low variation."
    }
  },
  "status": "classified"
}
```

---

### `POST /appeal`

Allows a creator to contest a classification.

Example request:

```json
{
  "content_id": "generated-content-id",
  "creator_reasoning": "I wrote this myself and can provide earlier drafts and notes."
}
```

Example response:

```json
{
  "appeal_id": "generated-appeal-id",
  "content_id": "generated-content-id",
  "creator_reasoning": "I wrote this myself and can provide earlier drafts and notes.",
  "status": "under_review"
}
```

When an appeal is submitted, Provenance Guard does not automatically reverse the classification. Instead, it updates the content status to `under_review` so a platform moderator or review process can evaluate the creator's explanation.

---

### `GET /log`

Returns recent structured audit log entries.

This endpoint is included for demonstration and grading visibility. In a real production system, this would likely be protected behind admin authentication.

---

### `GET /health`

Returns a simple health check response to confirm that the API is running.

---

## Detection Signals

Provenance Guard uses a multi-signal detection pipeline. A single signal is not enough because attribution detection is uncertain and creative writing varies widely by author, genre, and context.

This project uses two distinct signals:

### Signal 1: LLM Attribution Judge

The LLM attribution signal asks a language model to evaluate whether the submitted text appears more likely to be AI-generated, human-written, or mixed/uncertain.

This signal is useful because it can evaluate higher-level writing patterns such as generic phrasing, over-polished structure, repetitive transitions, and lack of concrete personal detail. These are difficult to capture with simple keyword rules.

However, this signal is not treated as absolute truth. LLMs can be wrong, especially with polished human writing, edited writing, or short excerpts. That is why the system combines the LLM judgment with a second signal instead of relying on it alone.

### Signal 2: Stylometric Heuristics

The stylometric signal measures surface-level writing patterns, including sentence length consistency, word variation, and structural regularity.

This signal is useful because AI-generated writing often has unusually smooth structure, consistent sentence lengths, and predictable transitions. Human writing may show more uneven rhythm, informal phrasing, interruptions, or idiosyncratic style.

This signal is intentionally heuristic. It does not prove authorship, but it provides a second perspective that is different from the LLM judge.

### Why These Signals?

I chose these two signals because they capture different properties of the text:

* The LLM judge captures semantic and rhetorical patterns.
* The stylometric signal captures measurable structure and variation.

Using both makes the system more reliable than a single detector because the final classification depends on agreement or tension between different types of evidence.

If I were deploying this system for real, I would add more signals, including metadata-based signals, creator writing history, revision history, and cryptographic provenance from trusted writing tools. I would also evaluate the model against a labeled benchmark dataset before using it in production.

---

## Confidence Scoring and Uncertainty

The system produces a confidence score instead of only returning a binary label. This is important because attribution analysis is probabilistic. A score near the middle should not be presented the same way as a score near 0.95.

The scoring system combines the AI-likelihood scores from the detection signals into one final probability. A score close to `1.0` means the system found stronger evidence of AI generation or heavy AI shaping. A score close to `0.0` means the system found stronger evidence of primarily human writing. A score near the middle means the system is uncertain.

The classification thresholds are:

```text
AI probability >= 0.75  -> likely_ai
AI probability <= 0.25  -> likely_human
Otherwise              -> uncertain
```

The returned confidence score represents how confident the system is in the displayed classification, not a guarantee of authorship.

For example:

* If the AI probability is `0.91`, the result is `likely_ai` with confidence `0.91`.
* If the AI probability is `0.18`, the result is `likely_human` with confidence `0.82`.
* If the AI probability is `0.54`, the result is `uncertain` with confidence `0.54`.

This makes a `0.51` result meaningfully different from a `0.95` result. A score near `0.51` should produce an uncertain label, while a score near `0.95` should produce a high-confidence attribution label.

### Example High-Confidence Case

Input excerpt:

```text
Artificial intelligence represents a transformative paradigm shift in modern society.
It is important to note that while the benefits of AI are numerous, it is equally
essential to consider the ethical implications. Furthermore, stakeholders across
various sectors must collaborate to ensure responsible deployment.
```

Example result:

```json
{
  "result": "likely_ai",
  "confidence": 0.91,
  "label_type": "high_confidence_ai"
}
```

This received a high-confidence AI result because both signals found patterns associated with AI-shaped writing: polished generalization, predictable transitions, and consistent structure.

### Example Lower-Confidence / Uncertain Case

Input excerpt:

```text
ok so i finally tried that new ramen place downtown and honestly?
underwhelming. the broth was fine but they put WAY too much sodium in it and
i was thirsty for like three hours after.
```

Example result:

```json
{
  "result": "uncertain",
  "confidence": 0.58,
  "label_type": "uncertain"
}
```

This received a lower-confidence result because the signals were less aligned. The informal style and uneven rhythm looked more human, but short or casual text can be difficult to classify reliably. The system therefore avoids pretending to know more than it does.

---

## Transparency Labels

The transparency label is the text that a reader would see on the creative sharing platform.

The label avoids saying “proven AI” or “proven human” because the system is probabilistic. It uses careful language such as “likely,” “signals,” and “automated analysis.”

| Label Variant         | Exact Text                                                                                                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| High-confidence AI    | "Provenance Guard found strong signals that this text was likely generated or heavily shaped by AI. This label is based on automated analysis and may be appealed by the creator." |
| High-confidence human | "Provenance Guard found strong signals that this text was likely written primarily by a person. This label is based on automated analysis and is not a guarantee of authorship."   |
| Uncertain             | "Provenance Guard could not determine a confident attribution for this text. The available signals were mixed, so readers should treat the authorship as uncertain."               |

---

## Appeals Workflow

Creators can contest a classification by submitting an appeal.

An appeal captures:

* The original content ID
* The creator's reasoning
* The original classification result
* The original confidence score
* The updated status
* A timestamp

When an appeal is submitted, the content status changes from `classified` to `under_review`.

This design keeps the system fairer because a creator is not trapped by an automated label. The appeal does not automatically change the result, but it creates a clear review trail for a human moderator or future review process.

Example appeal record:

```json
{
  "appeal_id": "appeal-001",
  "content_id": "content-001",
  "creator_reasoning": "I wrote this myself and can provide earlier drafts.",
  "original_result": "likely_ai",
  "original_confidence": 0.91,
  "updated_status": "under_review",
  "created_at": "2026-06-30T12:47:55.821072+00:00"
}
```

---

## Rate Limiting

The API uses rate limiting to reduce abuse, prevent accidental request loops, and control the cost of expensive attribution analysis.

Chosen limits:

```text
POST /submit: 10 requests per minute per client IP
POST /appeal: 5 requests per minute per client IP
GET /log: 30 requests per minute per client IP
```

Reasoning:

The submission endpoint is the most expensive because it runs the detection pipeline and may call an external LLM. Ten requests per minute is enough for development and demo use while still preventing spam or accidental infinite loops.

The appeal endpoint has a lower limit because appeals should be much lower volume than submissions. Five appeals per minute is enough for normal use while discouraging abuse.

The log endpoint is cheaper, so it allows more requests. Thirty requests per minute is enough for testing and demonstration without leaving the endpoint completely unrestricted.

### Rate Limit Testing

To verify rate limiting, I sent repeated requests to `/submit` within one minute. The first 9 requests succeeded with `200 OK`. Additional requests in the same one-minute window returned `429 Too Many Requests`. This was due to making a submission in the same one minute window used during testing.

Example Flask output:

```text
127.0.0.1 - - [30/Jun/2026 14:46:57] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:16] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:17] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:17] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:18] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:18] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:19] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:19] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:19] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:20] "POST /submit HTTP/1.1" 200 -
127.0.0.1 - - [30/Jun/2026 14:47:20] "POST /submit HTTP/1.1" 429 -
127.0.0.1 - - [30/Jun/2026 14:47:20] "POST /submit HTTP/1.1" 429 -
127.0.0.1 - - [30/Jun/2026 14:47:20] "POST /submit HTTP/1.1" 429 -
```

---

## Structured Audit Log

Every attribution decision and appeal is written to a structured JSONL audit log.

The audit log captures:

* Timestamp
* Event type
* Content ID
* Creator ID
* Classification result
* Confidence score
* Label type
* Transparency label
* Signals used
* Appeal information, if applicable
* Updated status

This creates an accountability trail. A platform operator can inspect why a piece of content received a label, what signals contributed to the decision, and whether the creator appealed.

Example audit log entries:

```json
{"timestamp":"2026-06-30T12:40:10.123456+00:00","event_type":"content_classified","content_id":"content-001","creator_id":"creator-001","result":"likely_ai","confidence":0.91,"label_type":"high_confidence_ai","signals":{"llm_judge":{"score":0.94,"explanation":"The text uses polished generalized phrasing."},"stylometry":{"score":0.78,"explanation":"The text has highly consistent sentence structure."}},"status":"classified"}
{"timestamp":"2026-06-30T12:42:31.456789+00:00","event_type":"content_classified","content_id":"content-002","creator_id":"creator-002","result":"likely_human","confidence":0.87,"label_type":"high_confidence_human","signals":{"llm_judge":{"score":0.16,"explanation":"The text includes informal phrasing and specific personal detail."},"stylometry":{"score":0.22,"explanation":"The text has uneven rhythm and varied sentence structure."}},"status":"classified"}
{"timestamp":"2026-06-30T12:47:55.821072+00:00","event_type":"appeal_submitted","appeal_id":"appeal-001","content_id":"content-001","creator_reasoning":"I wrote this draft myself and can provide earlier notes.","original_result":"likely_ai","original_confidence":0.91,"updated_status":"under_review"}
```

---

## Known Limitations

Provenance Guard can be wrong. The system should be treated as a decision-support tool, not a source of absolute truth.

One specific type of content this system would likely struggle with is polished academic or professional writing written by a human. This kind of writing often uses formal transitions, consistent sentence structure, and generalized phrasing. Those are also properties that both the LLM judge and stylometric signal may associate with AI-generated writing, so the system could incorrectly classify polished human writing as AI-shaped.

The system may also struggle with very short submissions. Short text does not provide enough evidence for reliable stylometric analysis, and the LLM judge may overinterpret a small sample.

Another limitation is that the current system does not use creator history, draft history, keystroke/revision metadata, or cryptographic proof of authorship. In a production system, those signals would make attribution decisions more reliable and fair.

---

## Spec Reflection

The planning spec helped guide the implementation because it forced me to define the detection signals, scoring thresholds, label variants, audit log fields, and appeal flow before writing the code. This made the implementation more consistent because each module had a clear responsibility.

One place the implementation diverged from the original spec was endpoint naming. The original planning language used `/analyze`, but the implementation uses `/submit` to better match the product flow: a creator submits content, and the system returns an attribution analysis. The underlying behavior stayed aligned with the spec, but the endpoint name became clearer.

Another small divergence is that the current appeals workflow does not perform automated re-classification. I chose this intentionally because the requirement only asks for the appeal to capture the creator's reasoning, log the appeal, and update the status to `under_review`. Human review is a safer next step than automatically reversing or re-running an uncertain classification.

---

## AI Usage

I used AI assistance during the project, but I made the architecture and implementation decisions myself and revised the generated code to match the project requirements.

### Instance 1: Planning the Architecture

I directed the AI to help turn the project requirements into a backend architecture with clear components: API layer, rate limiter, detection pipeline, scoring engine, label generator, content store, audit log, and appeals workflow.

The AI produced a draft architecture narrative and diagram structure. I revised it to fit my actual project, including the exact endpoint flow and the requirement that the diagram live in `planning.md` under the `## Architecture` section.

### Instance 2: Implementing the Detection and Scoring Modules

I directed the AI to help draft the detector, scoring, and label modules based on my planned thresholds and signal descriptions.

The AI produced initial Python functions for combining signal scores and mapping scores to label types. I reviewed and adjusted the logic so that confidence behaved meaningfully: high AI probability maps to `likely_ai`, low AI probability maps to `likely_human`, and middle scores map to `uncertain`.

### Instance 3: Debugging Integration Issues

I used AI help to review integration issues between `app.py`, `audit.py`, and the appeals workflow.

The AI helped identify mismatches such as inconsistent names for submission/content IDs and endpoint naming. I revised the code so the API response, stored submission, appeal record, and audit log all used consistent fields.

---

## How to Run the Project

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file if using an external LLM provider:

```bash
GROQ_API_KEY=your-api-key-here
```

Run the Flask app:

```bash
python app.py
```

Test the health endpoint:

```bash
curl http://127.0.0.1:5000/health
```

Submit content:

```bash
curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "creator_id": "creator-001",
    "text": "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that stakeholders must collaborate to ensure responsible deployment."
  }'
```

Submit an appeal:

```bash
curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "replace-with-real-content-id",
    "creator_reasoning": "I wrote this myself and can provide earlier drafts."
  }'
```

View audit log entries:

```bash
curl http://127.0.0.1:5000/log
```

---