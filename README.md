# ResolveAI
### An AI-Powered Customer Support Resolution Agent

ResolveAI is a customer-support automation prototype combining a language model, retrieval-augmented generation (RAG), deterministic business rules, database-backed tools, evidence upload, and a support operations dashboard.

Rather than acting only as a chatbot, ResolveAI is designed to understand a request, retrieve relevant policy information, check available order data, apply backend rules, perform a permitted action when eligible, and return a clear result or escalate when it cannot safely proceed.

> **Project status:** Working portfolio prototype. Core support, policy-answering, damaged-product evidence, duplicate-replacement protection, and order-ownership flows have been exercised manually. This is not a production-ready customer-service platform.

## Contents

- [Problem statement](#problem-statement)
- [Goals and features](#goals-and-features)
- [Architecture](#architecture)
- [Why RAG?](#why-rag)
- [RAG versus alternatives](#rag-versus-alternatives)
- [Request lifecycle](#request-lifecycle)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [Setup](#setup)
- [API overview](#api-overview)
- [Safety and reliability](#safety-and-reliability)
- [Manual testing](#manual-testing)
- [Limitations](#limitations)
- [Future improvements](#future-improvements)
- [Learning outcomes](#learning-outcomes)
- [License](#license)

## Problem statement

Customer-support teams handle repeated questions about returns, refunds, delivery, payments, and damaged products. A simple FAQ bot may answer questions but cannot necessarily complete an operational workflow. A general-purpose language model may also provide plausible-sounding answers without checking the current company policy or the customer's actual order.

ResolveAI explores a more grounded approach: natural-language understanding connected to policy retrieval, structured application data, deterministic business rules, controlled tools, case tracking, and escalation.

### Example

A customer writes:

> My order ORD-48393 arrived damaged and I need a replacement.

The intended workflow is to detect the damaged-product intent, retrieve the relevant policy, look up the order, verify ownership and eligibility, request a photo if required, re-check the case after upload, check for an existing replacement, and create a replacement request only when permitted. The result is returned to the customer and visible to the support team.

The language model helps interpret and communicate. The backend remains responsible for data access and operational decisions.

## Goals and features

### Customer experience
- Natural-language support requests.
- Policy questions that do not require an order number or customer ID.
- Order-specific flows for supported intents.
- Structured responses with case ID, intent, status, response, evidence, actions, and escalation details.
- Damaged-product evidence upload for JPG, PNG, and WebP files, with an 8 MB size limit.

### AI and retrieval
- Intent detection for supported request categories.
- Policy retrieval using ChromaDB.
- Policy-grounded response generation using a Groq-hosted language model.
- Fallback handling when retrieval or generation cannot provide a sufficiently supported answer.

### Backend and operations
- FastAPI API routes.
- SQLAlchemy models backed by SQLite for local development.
- Database-backed customer, product, order, payment, return, refund, support-case, and audit data.
- Controlled backend tools for supported operations.
- Eligibility checks and duplicate replacement protection.
- Order-to-customer ownership checks and escalation for mismatched ownership.
- Support case list, search, status filtering, case details, investigation evidence, and administrative handling.

## Architecture

```text
Customer
   |
   v
React + Vite Customer Portal
   |
   v
FastAPI: POST /api/support
   |
   +--> Intent detection
   |
   +--> Policy question -----------------------+
   |                                           |
   |                                           v
   |                                    ChromaDB retrieval
   |                                           |
   |                                           v
   |                                    Relevant policy text
   |                                           |
   |                                           v
   |                                    Groq language model
   |
   +--> Order-specific request
                |
                v
        Customer/order lookup
                |
                v
        Ownership and eligibility checks
                |
                v
        Required evidence present?
             /          \
           No            Yes
           |              |
           v              v
   Ask for evidence   Controlled backend tool
           |              |
           v              v
     Evidence upload   Return/replacement/etc.
           |              |
           +------<-------+
                |
                v
      Support case + audit record
                |
                v
      Customer response / escalation
                |
                v
       React Support Operations Dashboard
```

This is a conceptual view of the workflow. Exact execution depends on the detected intent and the implemented handler.

### Core design principle

**The language model should not be the authority for business permissions.** A model can classify requests, use retrieved policy text, and write responses. It should not independently decide that a refund is eligible or that an order belongs to a customer. Those checks belong in backend code and database-backed rules.

## Why RAG?

RAG stands for **Retrieval-Augmented Generation**. It combines retrieving relevant information from a knowledge source with generating a response that uses that information.

ResolveAI uses RAG for company-policy questions because policy is reference material that can change and should be traceable to a source.

### How RAG works here

1. **Prepare policy documents.** Policy text is organized into categories such as returns, refunds, damaged products, delivery, payment, cancellation, and general support.
2. **Index the policy text.** ChromaDB stores the policy collection for retrieval.
3. **Receive a question.** Example: “Can I return an item delivered last week?”
4. **Retrieve relevant text.** The retrieval layer searches for policy content related to the question.
5. **Generate a grounded answer.** The language model receives the question and retrieved policy context and produces a readable response.
6. **Handle weak retrieval.** If no sufficiently relevant policy is found, the application can use a fallback path instead of pretending a matching policy was found.

### Why not ask the LLM alone?

A language model's training does not guarantee it knows the current policies of a particular application. Asking it alone can lead to invented deadlines or exceptions, generic answers that conflict with company rules, or answers that cannot be traced to a source. RAG supplies the application's policy text at request time, making answers easier to ground in the intended knowledge source.

### Why not hard-code every policy in Python?

Hard-coded rules are useful for exact decisions, such as a seven-day eligibility window or an allowed payment status. They are less convenient as the only storage mechanism for long policy documents. With all policy text hard-coded, updates may require code edits, paraphrased questions require more manual matching logic, and the knowledge base becomes harder to maintain.

RAG separates policy text retrieval from application workflow code. Deterministic rules still belong in code when an outcome must be precise.

### Why not use RAG for everything?

RAG is not a database and does not replace business rules.

| Task | Appropriate approach | Reason |
|---|---|---|
| Explain return policy | RAG + LLM | Retrieve policy text and explain it naturally |
| Check whether an order exists | Database query | Exact structured lookup |
| Verify order ownership | Backend rule | Must be a deterministic authorization check |
| Check delivery date and eligibility | Backend rule | Requires precise comparisons and defined rules |
| Prevent duplicate replacements | Database/tool logic | Check existing records before creating a new one |
| Explain the result | LLM with verified context | Produces a clear customer-facing response |
| Record workflow events | Database/audit service | Persistent history for debugging and review |

RAG does not guarantee correctness. Retrieval can return incomplete or weakly relevant text, and a model can misinterpret retrieved information. Quality depends on source documents, chunking, embeddings, retrieval thresholds, and prompting. A larger deployment should evaluate retrieval relevance and answer faithfulness against a representative question set.

## Request lifecycle

1. **Intake:** The frontend sends a support message to FastAPI. The backend creates a case and detects an intent.
2. **Routing:** The application routes the request into a supported path, such as policy question, damaged product, return, refund, delivery, payment, cancellation, or general query.
3. **Policy path:** Relevant policy context is retrieved and passed to the language model to generate a grounded response. If the answer cannot be supported, fallback or escalation may be used.
4. **Order path:** The backend looks up the order and checks whether its customer matches the customer identifier supplied for the request.
5. **Evidence collection:** A damaged-product request can wait for a photograph. The evidence endpoint checks file type, size, and basic file signature, records the upload event, and reruns the agent.
6. **Controlled action:** Backend tools perform supported operations. Checks such as duplicate replacement protection run before creating a new request.
7. **Case update:** The support case is updated with status, response, and any escalation reason. Important events can be written to the audit log.
8. **Dashboard:** Support staff can review cases, detected intents, statuses, and investigation details.

## Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React | Customer portal and support dashboard |
| Frontend tooling | Vite | Development server and build tooling |
| Backend API | FastAPI | HTTP endpoints and request validation |
| ORM | SQLAlchemy | Database models and queries |
| Local database | SQLite | Persistent local development data |
| Language model | Groq API, `openai/gpt-oss-20b` | Natural-language responses and intent handling |
| Retrieval store | ChromaDB | Policy text storage and retrieval |
| Validation | Pydantic | Request validation |
| Evidence upload | FastAPI `UploadFile` | Image upload handling |

Use the actual dependency files in the repository as the source of truth for installed versions.

## Project structure

```text
ResolveAI/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── agent.py
│   │   │   └── llm.py
│   │   ├── api/routes/
│   │   │   ├── admin_cases.py
│   │   │   ├── cases.py
│   │   │   ├── evidence.py
│   │   │   ├── health.py
│   │   │   └── support.py
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/models.py
│   │   ├── rag/policies.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── audit.py
│   │   │   └── rules.py
│   │   ├── tools/tools.py
│   │   └── main.py
│   ├── tests/
│   │   └── test_rules.py
│   └── seed.py
├── frontend/
│   └── src/
│       ├── main.jsx
│       └── style.css
├── .env                 # Local secrets; never commit
└── README.md
```

This reflects the known layout. Review the actual project tree before publishing, and do not commit generated databases, uploads, virtual environments, dependency folders, or build artifacts unless intentionally required.

## Setup

### Prerequisites
- Python 3.12 recommended for the current development setup.
- Node.js and npm compatible with the Vite project.
- A Groq API key for language-model features.
- Git.

### 1. Clone the repository

After publishing it to GitHub:

```bash
git clone https://github.com/<YOUR_USERNAME>/ResolveAI.git
cd ResolveAI
```

Replace `<YOUR_USERNAME>` with your GitHub username.

### 2. Create a Python virtual environment

From the repository root:

**Windows Command Prompt**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

Install backend dependencies using the dependency file included in the repository. For example, if `backend/requirements.txt` exists:

```cmd
cd backend
pip install -r requirements.txt
```

If your dependencies are recorded in another file, use that file instead. Confirm the dependency filename before publishing these commands.

### 3. Configure environment variables

Create a local `.env` file in the location expected by the backend configuration. The current development setup uses `GROQ_API_KEY` in the repository root.

```dotenv
GROQ_API_KEY=your_groq_api_key_here
```

Use your own key locally. **Never commit a real API key.** Add `.env` to `.gitignore`.

### 4. Start the backend

From the `backend` directory, with the virtual environment activated:

```cmd
uvicorn app.main:app --reload --port 8000
```

- API base: `http://127.0.0.1:8000`
- Interactive API docs: `http://127.0.0.1:8000/docs`

### 5. Start the frontend

Open a second terminal:

```cmd
cd frontend
npm install
npm run dev
```

Vite prints the local URL, commonly `http://localhost:5173`.

If the frontend uses `VITE_API_BASE_URL`, set it to the API prefix expected by the frontend, commonly:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Restart Vite after changing frontend environment variables.

## API overview

The paths below reflect the known support route and route layout. Use the running Swagger page at `/docs` as the source of truth for all registered methods and exact prefixes.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/support` | Create a support case and run the agent |
| `POST` | `/api/support/cases/{case_id}/evidence` | Upload evidence for a damaged-product case |
| `GET` | Health route | Check `/docs` for the registered path |
| Case routes | `/api/cases...` | Review and retrieve support cases; see `/docs` for methods |
| Admin case routes | Registered admin route | Administrative case actions; see `/docs` for exact paths |

### Example: general policy question

```json
{
  "message": "What is your return policy?"
}
```

### Example: order-specific damaged-product request

```json
{
  "message": "I am customer CUST-1001. My order ORD-48393 arrived damaged and I need a replacement."
}
```

### Example response shape

```json
{
  "case_id": "CASE-EXAMPLE",
  "status": "WAITING_FOR_INFORMATION",
  "intent": "DAMAGED_PRODUCT",
  "response": "Please upload a photograph of the damaged product.",
  "evidence": [],
  "actions": [],
  "escalation_reason": null
}
```

Values are illustrative. Actual status and response depend on request content, order state, policy, evidence, and existing records.

## Safety and reliability

### Ownership checks

The backend checks whether the order's `customer_id` matches the customer identifier associated with the request. In a manual test, a mismatched customer ID resulted in `ESCALATED`, an ownership-related reason, and no replacement action.

**Important prototype limitation:** a customer ID typed into a message is not proof of identity. A public deployment must authenticate the user and derive the customer identity from a trusted session or token, rather than trusting free text or a client-supplied ID.

### Duplicate protection

Before creating a replacement request, the backend checks whether a replacement already exists for the order. In manual testing, repeating the request returned the existing replacement ID rather than creating a second request.

### Evidence validation

The evidence endpoint enforces a size limit, accepts configured image formats, checks basic file signatures, associates evidence with the order in the case, and records an audit event. This is basic validation, not a complete malware-scanning or image-safety system.

### Deterministic business rules

Eligibility and authorization decisions should be enforced in backend code using database state, not solely by the language model. Policy text explains the rules; application code enforces operational constraints.

### Audit trail

Important workflow events, including evidence upload, can be recorded for investigation and debugging.

## Manual testing

These scenarios have been exercised manually during local development. They are not a comprehensive automated test suite.

| Scenario | Expected behavior | Observed result |
|---|---|---|
| Ask about return policy | Retrieve policy context and return a grounded answer | Passed |
| Damaged-product request without customer details | Ask for required details before running the order action | Passed |
| Matching customer and damaged order | Check order, policy, evidence, and existing replacement | Passed |
| Upload damage evidence | Record evidence and rerun the workflow | Passed in the demonstrated flow |
| Repeat a replacement request | Detect existing replacement and avoid duplication | Passed |
| Mismatched customer ID | Escalate and avoid replacement action | Passed |

Example ownership-protection response:

```json
{
  "status": "ESCALATED",
  "intent": "DAMAGED_PRODUCT",
  "response": "I could not verify that order under your customer account.",
  "actions": [],
  "escalation_reason": "Order does not belong to customer"
}
```

### Additional tests recommended before production

- Automated API tests for supported intents.
- Policy retrieval quality and fallback tests.
- Empty, oversized, spoofed, and invalid image upload tests.
- Concurrent duplicate-request tests.
- Refund and return edge cases.
- Database migration and recovery tests.
- Authentication and authorization tests.
- Frontend production build and browser tests.

Do not describe these additional tests as passed until they have been run.

## Limitations

ResolveAI is an academic/portfolio prototype. It should not be deployed as a public production support system without further work.

1. **Authentication:** Customer IDs are not secure authentication. Add session/token authentication and derive identity server-side.
2. **Status semantics:** An existing replacement request is not the same as a replacement that has shipped or been delivered. Case states and customer-facing labels should distinguish these conditions.
3. **Policy/rule alignment:** Keep policy text, eligibility functions, and tool-level validation consistent, particularly for payment statuses, refund amounts, deadlines, and returns.
4. **LLM uncertainty:** Outputs can be wrong. Add evaluation data, structured output validation, and handling for low-confidence or malformed responses.
5. **Evidence storage:** Local disk storage suits development. Production needs access control, retention rules, backups, and secure object storage.
6. **Observability:** Add structured logs, metrics, tracing, and clearer operational error reporting.
7. **Testing:** Manual checks do not replace a comprehensive automated suite.
8. **External integrations:** Real payment, shipping, notification, and human-agent systems need secure integrations and failure handling.
9. **Privacy:** Production needs data minimization, retention policies, and controls around customer images and personal data.

## Future improvements

- Authentication and role-based access control.
- Human approval for high-risk actions.
- Explicit case-state transitions, such as `WAITING_FOR_INFORMATION`, `ESCALATED`, `REQUEST_RECORDED`, and `RESOLVED`.
- An audit history linking each action to its case and actor.
- Policy versioning and policy-source citations in responses.
- Retrieval evaluation with representative questions and relevance metrics.
- Automated tests for routes, rules, tools, and frontend workflows.
- Secure object storage for evidence.
- Human handoff with a structured summary of issue, order facts, policy context, and actions already taken.
- CI checks and a production database such as PostgreSQL.

## Learning outcomes

This project demonstrates practical work across:
- LLM integration in a backend application.
- RAG for domain-specific knowledge grounding.
- Tool-based AI workflows.
- Separation of probabilistic language understanding from deterministic business logic.
- REST API development with FastAPI and Pydantic.
- SQLAlchemy relational data modeling.
- Evidence upload and file validation.
- Duplicate-operation prevention and data ownership checks.
- React interfaces and support operations dashboards.
- Auditability, failure handling, and safer AI application design.

## License

Choose a license before making the repository public. If you want others to use, modify, and distribute the project, add a license file such as the MIT License. Do not claim an open-source license until the corresponding `LICENSE` file has been added.

## Author

**Your Name**

AI Engineering · Backend Development · Retrieval-Augmented Generation · Applied Machine Learning

Replace this section with your preferred name, GitHub profile, LinkedIn profile, and contact information before publishing.

## Suggested GitHub repository description

> AI-powered customer support resolution agent using FastAPI, React, RAG, ChromaDB, and a Groq-hosted LLM. Includes policy-grounded answers, order workflows, evidence upload, duplicate protection, and support case management.

### Suggested repository topics

`artificial-intelligence` `rag` `llm` `fastapi` `react` `chromadb` `customer-support` `generative-ai` `python` `sqlalchemy`
