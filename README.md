# adk-insurance-lab
insurance + Google ADK + multi-agent workflows


Use Case: Automated Claims Processing & Validation Assistant
Business Problem
Insurance claims processing involves multiple steps:

Collecting claim details (structured + unstructured docs)

Validating policy coverage

Checking for fraud

Estimating payout

Notifying customer

This is usually manual, slow, and error-prone.

🔹 How Google ADK fits
Sequential Workflow (Step-by-Step Claims Flow)

Agent A (Data Ingestion Agent): Reads claim form, extracts key info (policy number, damage description).

Agent B (Policy Validation Agent): Checks coverage rules (does policy cover this type of claim?).

Agent C (Fraud Check Agent): Flags suspicious patterns (duplicate claims, unusual claim sizes).

Agent D (Payout Estimator): Suggests a settlement amount based on claim type + history.

Each runs sequentially, passing output to the next step.

Parallel Workflow (Faster Validation)

Policy Validation Agent and Fraud Check Agent can run in parallel because they don’t depend on each other.

This cuts processing time (important for scaling).

Multi-Agent Workflow (Specialized Collaboration)

A Coordinator Agent (like an ADK “router”) decides which specialized agents to trigger:

Simple claims? → Skip Fraud Check, just Policy Validation + Payout.

Complex/high-value claims? → Run all agents including Fraud + Extra Audit Agent.

This shows ADK’s ability to route dynamically and avoid wasted compute.

🔹 Why This is a Good POC
Simple enough to demo quickly (small dataset, mock rules).

Relatable business value → faster, more accurate claims processing.

Highlights ADK strengths:

Sequential workflows (A → B → C → D).

Parallel workflows (fraud + validation).

Multi-agent collaboration (different “experts” working together).

🔹 Extra “Wow Factor” for POC
Show explainability: each agent outputs reasoning (why it flagged fraud, why it validated policy).

Add tool use: e.g. Fraud Check Agent queries a mock “fraud database API.”

Keep mock data (no sensitive info) — just a few sample claims in CSV/JSON.