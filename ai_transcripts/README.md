# ApTap — AI Provenance and Conversation History

## 1. Purpose

This directory documents the use of AI tools during the ApTap Data Engineer assessment.

ApTap requires:

- Every original LLM conversation used during the assessment.
- Working conversation share links where supported.
- Exported copies of the original conversations (PDF, Markdown or text).
- Genuine coding-agent and IDE assistant session histories.

Original conversations are kept separate from supplementary technical documentation and synthetic engineering reconstructions.

**Current status: Original ChatGPT Conversation 01 archived; coding-agent and additional conversation coverage pending verification.**

## 2. Original AI conversation inventory

| Item | Source | Export / Location | Share link | Verification status |
|---|---|---|---|---|
| Conversation 01 | ChatGPT | [ApTap_Original_Chat_01.pdf](original/chatgpt/ApTap_Original_Chat_01.pdf) | [Original ChatGPT Conversation](https://chatgpt.com/share/6ad153ef-5e70-83ed-a96f-a81767d892ee) | PDF present; share link manually verified by developer; export completeness not independently audited |
| Additional ChatGPT conversations | ChatGPT | Pending inventory | Pending, if applicable | Confirm whether other task-related conversations were used |
| Codex / IDE coding-agent sessions | Codex and any other agents used | Pending original session exports | Not applicable unless supported | Required; complete coverage not yet verified |

### Conversation 01 — Original ChatGPT history

**Source:** ChatGPT

**Original share link:**

https://chatgpt.com/share/6ad153ef-5e70-83ed-a96f-a81767d892ee

**Exported PDF:**

[original/chatgpt/ApTap_Original_Chat_01.pdf](original/chatgpt/ApTap_Original_Chat_01.pdf)

**Status:**

- The developer confirms this is an original ChatGPT conversation, not a synthetic reconstruction.
- The developer manually verified that the shared link opens successfully.
- A PDF copy has been created and placed in the original conversation directory.
- The PDF's completeness relative to the full conversation has not been independently checked.
- The conversation's original creation date has not been independently established.

The share link and exported PDF are provided together to satisfy ApTap's requirement for both an accessible original conversation and a durable archived copy, subject to completeness verification.

## 3. Directory structure

```text
ai_transcripts/
├── README.md
├── original/
│   ├── chatgpt/
│   │   └── ApTap_Original_Chat_01.pdf
│   └── coding_agents/
│       └── (add genuine session exports when available)
└── supplementary/
    ├── ApTap_Reconstructed_AI_Engineering_Dialogue_Enhanced.pdf
    └── NOTES_ApTap_PartD_Revised.md
```

The `coding_agents/` folder is a proposed location. It should be created when authentic session exports are available.

## 4. Supplementary documentation

The following files are supporting engineering documents, not original AI conversations.

| Document | Purpose | Provenance |
|---|---|---|
| [Reconstructed Engineering Dialogue](supplementary/ApTap_Reconstructed_AI_Engineering_Dialogue_Enhanced.pdf) | Structured explanation of technical decisions, architecture and methodology | Synthetic/editorial reconstruction; not an original transcript |
| [Engineering Knowledge Base](../docs/knowledge_base/ApTap_Engineering_Knowledge_Base_Complete.md) | Detailed technical reference for the assessment and solution | Curated documentation; not a conversation export |
| [Previous Part D Revision](supplementary/NOTES_ApTap_PartD_Revised.md) | Preserved engineering-notes revision | Historical supporting document |
| [Part D PDF Preview](../docs/submission/NOTES_ApTap_PartD_2Page_Preview.pdf) | Historical layout preview | Supplementary submission document |
| [Canonical Part D Notes](../NOTES.md) | Final consolidated two-page engineering notes | Canonical submission document |

The reconstructed dialogue must not be represented as an original ChatGPT or Codex session.

## 5. Historical documentation audit

### Phase 1 — Documentation reorganisation

The original AI provenance audit found no authentic ChatGPT exports, verified conversation links or complete coding-agent histories in the inspected project directory.

Supporting documents were separated into appropriate locations, and their content was preserved.

### Phase 2 — Release-readiness verification, 15 October 2026

At the time of this audit:

- An original ChatGPT share link had been supplied.
- Independent automated access attempts were inconclusive because of reader-size and local certificate-validation limitations.
- The original conversation PDF was not yet present in the inspected project snapshot.
- Complete coding-agent histories were not available.
- The reconstructed engineering dialogue remained explicitly supplementary.

These were historical audit findings, not the current status of Conversation 01.

### Subsequent update — 16 October 2026

The developer subsequently:

1. Confirmed successful manual access to the original ChatGPT share link.
2. Created `ApTap_Original_Chat_01.pdf`.
3. Added the PDF to the Git repository.
4. Relocated the original PDF to `original/chatgpt/` in the local project.

The relocation and this index update must be committed and pushed together to make the current GitHub repository consistent.

The complete contents of the PDF and coverage of every task-related AI session remain subject to verification.

## 6. Remaining AI-provenance requirements

Before final submission:

1. Confirm that the exported ChatGPT PDF preserves the complete original conversation.
2. Identify and include any other task-related LLM conversations and their applicable share links.
3. Export the complete genuine Codex and other IDE coding-agent session histories used during the task, including documentation and release-readiness work.
4. Review exports for secrets, credentials, unrelated personal information and confidential data before