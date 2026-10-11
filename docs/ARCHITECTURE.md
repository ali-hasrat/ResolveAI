# ResolveAI Architecture

## Request lifecycle

1. Customer sends natural-language request.
2. FastAPI creates a support case.
3. Agent detects intent.
4. Agent extracts an order identifier when required.
5. Controlled tools retrieve records.
6. Policy retrieval supplies operational rules.
7. Deterministic business rules validate eligibility.
8. Approved operations are executed.
9. Audit events are stored.
10. The customer receives a resolution or the case is escalated.

## Safety boundary

The language model is not the authority for database changes.

The backend is authoritative for:
- authorization
- eligibility
- amount validation
- duplicate prevention
- transaction execution
- audit logging

## Future production extensions

- JWT authentication
- role-based authorization
- true LangGraph state machine
- semantic Chroma retrieval
- LLM-generated natural-language explanations
- image evidence storage
- human approval endpoint
- Redis idempotency keys
- OpenTelemetry
- Dockerized frontend/backend
- CI/CD
