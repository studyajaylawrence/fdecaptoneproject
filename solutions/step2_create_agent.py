#!/usr/bin/env python3
"""LAB PART 2 - build the grounded agent.

Two things happen here:

  1. A project connection is created so the agent can call your knowledge base with the
     project's managed identity (no keys).
  2. An agent version is created with the knowledge base attached as an MCP tool, your
     instructions, and a strict JSON response contract.

Run:
    python step2_create_agent.py            # create connection + agent
    python step2_create_agent.py --ask "..." # ask your agent one question

REFERENCE SOLUTION. Compare with your own version rather than starting here.
"""
from __future__ import annotations

import argparse
import json

import requests
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import AzureCliCredential

import lab_config as cfg

# --------------------------------------------------------------------- instructions

INSTRUCTIONS = """
You are the Contoso Health System Clinical Knowledge Assistant. You support care
coordination. You never replace clinical judgement.

GROUNDING
1. You have one tool: the approved-corpus knowledge base. Call it for every question about
   clinical guidance, policy, pathways or process, before you answer.
2. Answer only from what the tool returns. Never use your own medical knowledge, and never
   use outside sources, even when you are confident.
3. If the tool returns nothing relevant, say plainly that the approved corpus does not cover
   the question, and set requires_clinician_review to true.

CITATIONS
4. Every substantive claim must be traceable to a retrieved document. Populate `citations`
   with the document names or titles the tool returned, plus the section where available.
   Never invent a citation, a document name, a section number or a URL.
   A citation entry may only name a document that actually appeared in the retrieved results.
   If retrieval returned nothing relevant, or you are refusing, leave `citations` empty rather
   than echoing back a document name from the question. Naming a document in order to say it
   was not found belongs in `answer`, never in `citations`.

CONFIDENCE (policy CHS-POL-001 section 5)
5. Set exactly one confidence value:
   - "High": every claim comes from a direct statement in a single approved document.
   - "Moderate": the answer combines two or more documents, or paraphrases indirect statements.
   - "Low": retrieval is partial, ambiguous, out of date, conflicting, or the corpus does not
     answer the question.

CLINICIAN DEFERRAL (policy CHS-POL-001 section 4)
6. Do not answer, and instead defer, when the request:
   - concerns a specific identifiable patient, or contains protected health information;
   - asks for a diagnosis, or whether to start, stop or change treatment;
   - asks for a dose, titration or infusion rate for a patient;
   - concerns a paediatric, pregnant or clinically unstable patient;
   - asks you to interpret an individual patient's results or images;
   - concerns end-of-life decisions, capacity or consent.
   When you defer, `answer` must contain ONLY: one sentence saying this is a clinical decision
   and why, and the escalation route from CHS-POL-002. Do not include guideline content,
   thresholds, doses, referral criteria, differential reasoning or "helpful context" of any
   kind, even when retrieval returned it. Cite only the policy that requires the deferral.
   Set requires_clinician_review to true.
7. Set requires_clinician_review to true whenever confidence is "Low", whenever you deferred,
   and whenever you cannot cite a source.

PHI (policy CHS-POL-004 section 2)
8. If the question contains patient identifiers, do not repeat them back anywhere in your
   response. Explain that this assistant is not approved to receive PHI, and defer.

STYLE
9. Be brief and concrete. Quote thresholds, timings and numbers exactly as the corpus states
   them. Use plain clinical English. Do not hedge with phrases like "consult your doctor"
   unless you are stating the deferral route.
10. Never put inline citation markers, reference brackets or tool annotations such as
    "[ref_id:1]" or "【6:1†source】" in any field, including citation details. Name documents
    and sections in plain text only.
""".strip()

# --------------------------------------------------------------------- response contract (given)

RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "confidence", "citations", "requires_clinician_review", "review_reason"],
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "string", "enum": ["High", "Moderate", "Low"]},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["document", "detail"],
                "properties": {"document": {"type": "string"}, "detail": {"type": "string"}},
            },
        },
        "requires_clinician_review": {"type": "boolean"},
        "review_reason": {"type": "string"},
    },
}


def create_connection() -> None:
    """Let the agent authenticate to the knowledge base as the project's managed identity."""
    access_token = AzureCliCredential().get_token("https://management.azure.com/.default").token
    headers = {"Authorization": f"Bearer {access_token}"}
    url = (f"https://management.azure.com{cfg.PROJECT_RESOURCE_ID}/connections/"
           f"{cfg.CONNECTION_NAME}?api-version=2025-10-01-preview")

    # GOTCHA: 'audience' is only applied when a connection is CREATED. Updating an existing
    # connection keeps the old value and the agent fails at run time with
    # "Failed to fetch access token ... Missing required query parameter 'audience'".
    requests.delete(url, headers=headers, timeout=60)

    response = requests.put(url, headers=headers, timeout=60, json={
        "name": cfg.CONNECTION_NAME,
        "type": "Microsoft.MachineLearningServices/workspaces/connections",
        "properties": {
            "authType": "ProjectManagedIdentity",
            "category": "RemoteTool",
            "target": cfg.KB_MCP_URL,
            "isSharedToAll": True,
            "audience": "https://search.azure.com/",
            "metadata": {"ApiType": "Azure"},
        },
    })
    response.raise_for_status()
    print(f"connection ready: {cfg.CONNECTION_NAME}")


def create_agent() -> None:
    knowledge_tool = MCPTool(
        server_label="approved_corpus",
        server_url=cfg.KB_MCP_URL,
        project_connection_id=cfg.CONNECTION_NAME,
        allowed_tools=["knowledge_base_retrieve"],
        require_approval="never",
    )

    project = AIProjectClient(endpoint=cfg.PROJECT_ENDPOINT, credential=AzureCliCredential())
    agent = project.agents.create_version(
        agent_name=cfg.AGENT_NAME,
        definition=PromptAgentDefinition(
            model=cfg.CHAT_DEPLOYMENT,
            instructions=INSTRUCTIONS,
            tools=[knowledge_tool],
            # "auto" would let the model answer without retrieving; "required" forbids that
            tool_choice="required",
            text={"format": {"type": "json_schema", "name": "clinical_answer",
                             "strict": True, "schema": RESPONSE_SCHEMA}},
        ),
    )
    print(f"agent ready: {agent.name} (version {getattr(agent, 'version', '?')})")


def ask(question: str) -> None:
    from ask_agent import ask as run          # noqa: PLC0415 - keeps the import local to this path
    result = run(question)
    print(json.dumps({k: v for k, v in result.items() if not k.startswith("_")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ask", metavar="QUESTION", help="ask your agent a question")
    args = parser.parse_args()

    if args.ask:
        ask(args.ask)
        return

    create_connection()
    create_agent()
    print("\nTry it:  python step2_create_agent.py --ask \"What does the sepsis pathway require in the first hour?\"")


if __name__ == "__main__":
    main()
