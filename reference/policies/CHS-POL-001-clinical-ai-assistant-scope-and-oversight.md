# CHS-POL-001 Clinical AI Assistant Scope and Human Oversight Policy

> **FICTIONAL TRAINING DOCUMENT.** Contoso Health System is not a real organisation. This
> content is written for the Microsoft FDE capstone lab and must never be used for real
> patient care.

| Field | Value |
|---|---|
| Document ID | CHS-POL-001 |
| Version | 4.2 |
| Effective date | 2026-07-01 |
| Next review | 2027-07-01 |
| Owner | Office of the Chief Medical Information Officer (CMIO) |
| Applies to | All Contoso Health System staff who use the Clinical Knowledge Assistant |

## 1. Purpose

This policy defines what the Clinical Knowledge Assistant ("the Assistant") may and may not do,
how it must present answers, and when it must hand a question to a clinician. The Assistant
supports care coordination. It never replaces clinical judgement.

## 2. Approved corpus

2.1 The Assistant may ground answers **only** on the Approved Clinical Corpus: VA/DoD Clinical
Practice Guidelines published on the corporate guideline shelf, NIH and NHLBI guidance, and
Contoso Health System policies and pathways carrying a CHS document ID.

2.2 If the Approved Clinical Corpus does not contain the answer, the Assistant must say that it
does not know, and must not answer from general knowledge.

2.3 Content outside the Approved Clinical Corpus, including web search results and model
pre-training knowledge, must not be presented as guidance.

## 3. In scope

The Assistant may answer:

- Navigation questions about guidelines, policies and pathways ("what does the sepsis pathway
  require in the first hour?").
- Questions about documentation standards, turnaround times and escalation routes.
- Definitional and threshold questions that are stated explicitly in the corpus.

## 4. Out of scope - mandatory clinician deferral

4.1 The Assistant must **decline and defer to a clinician** when a request:

- concerns a specific, identifiable patient, including any request that contains PHI;
- asks for a diagnosis, a treatment decision, or a recommendation to start, stop or change therapy;
- asks for a medication dose, titration, or infusion rate for a patient;
- concerns a paediatric, pregnant or critically unstable patient;
- asks the Assistant to interpret an individual patient's test results or images;
- concerns end-of-life decisions, capacity, or consent.

4.2 Deferral wording must name the responsible role, for example: "This is a clinical decision.
Please contact the attending clinician or the on-call service under CHS-POL-002."

## 5. Citations and confidence

5.1 Every substantive answer must carry at least one citation naming the source document and, where
available, the section or page.

5.2 Every answer must carry exactly one confidence label:

| Label | Meaning | Required handling |
|---|---|---|
| **High** | All claims are supported by a direct statement in a single approved document. | Answer may be used for care coordination. |
| **Moderate** | The answer combines two or more approved documents, or paraphrases indirect statements. | Answer must be verified by the requesting clinician before use. |
| **Low** | The corpus is partial, ambiguous, out of date, or conflicting. | Answer must be routed for clinician review before use. |

5.3 An answer with **Low** confidence, or any answer the Assistant cannot cite, must be routed for
clinician review and must not be acted on.

## 6. Human oversight

6.1 Every deferral and every Low-confidence answer must create a **clinician review item** in the
oversight queue, recording: the question, the drafted answer, the citations, the confidence label,
the reason for routing, the requester and the timestamp.

6.2 A licensed clinician must review each item and record one of: **approved**, **approved with
edits**, or **rejected**, together with a free-text note.

6.3 Review items must be acknowledged within **one business hour** for routine items. Items marked
urgent follow the response times in CHS-POL-002.

6.4 No answer routed for review may be released to the requester until a clinician has recorded a
decision. The Assistant must never mark its own work as reviewed.

## 7. Audit and retention

7.1 All Assistant interactions, review decisions and reviewer identities are retained for **seven
years** in the clinical audit store.

7.2 The CMIO office reviews a sample of at least **25 interactions per month**, and all rejected
items, at the Clinical AI Governance Committee.

7.3 Any answer found to be ungrounded, mis-cited or outside scope is logged as a **Category 2
safety event** and reported to the committee within five business days.

## 8. Related documents

- CHS-POL-002 Clinical Escalation and On-Call Contact Policy
- CHS-POL-004 PHI Handling and Minimum Necessary Standard
- CHS-PATH-010 Adult Sepsis Early Recognition and Response Pathway
