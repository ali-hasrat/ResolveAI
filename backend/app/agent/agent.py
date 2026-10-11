import re
from decimal import Decimal
from sqlalchemy.orm import Session

from app.tools.tools import (
    get_order,
    get_payment,
    create_return,
    request_refund,
    create_replacement,
)
from app.rag.policies import retrieve_policy_chunks, search_policy
from app.agent.llm import classify_intent, generate_answer
from app.services.audit import audit


def detect_intent(message: str) -> str:
    """Classify a support message with the configured LLM classifier."""
    return classify_intent(message)


def extract_order_id(message: str) -> str | None:
    match = re.search(r"\bORD-\d+\b", message.upper())
    return match.group(0) if match else None


def datetime_today():
    from datetime import date

    return date.today()


def _result(
    intent: str,
    status: str,
    response: str,
    evidence: list | None = None,
    actions: list | None = None,
    escalation_reason: str | None = None,
) -> dict:
    """Build a consistent result object for the support route."""
    result = {
        "intent": intent,
        "status": status,
        "response": response,
        "evidence": evidence or [],
        "actions": actions or [],
    }
    if escalation_reason:
        result["escalation_reason"] = escalation_reason
    return result


def _answer_policy_question(
    db: Session,
    customer_id: str,
    message: str,
    case_id: str,
    intent: str,
) -> dict:
    """Retrieve policy evidence and generate a grounded answer."""
    chunks = retrieve_policy_chunks(message)
    policy = "\n\n".join(
        f"Policy: {chunk['title']}\n{chunk['text']}" for chunk in chunks
    )

    audit(
        db,
        case_id,
        "POLICY_RETRIEVED",
        {"policy_count": len(chunks), "intent": intent},
    )

    if not policy.strip():
        return _result(
            intent=intent,
            status="ESCALATED",
            response=(
                "I couldn't find enough relevant policy information to answer "
                "reliably. Please contact a support representative."
            ),
            evidence=[],
            actions=[],
            escalation_reason="No relevant policy evidence retrieved",
        )

    try:
        response = generate_answer(question=message, policy_context=policy)
    except Exception as exc:
        audit(
            db,
            case_id,
            "LLM_GENERATION_FAILED",
            {"intent": intent, "error": str(exc)},
        )
        return _result(
            intent=intent,
            status="ESCALATED",
            response=(
                "I couldn't generate a reliable answer right now. Please try "
                "again or contact a support representative."
            ),
            evidence=[policy],
            actions=[],
            escalation_reason="LLM generation failed",
        )

    audit(
        db,
        case_id,
        "POLICY_ANSWER_GENERATED",
        {"intent": intent},
    )
    return _result(
        intent=intent,
        status="RESOLVED",
        response=response,
        evidence=[policy],
        actions=[],
    )


def run_agent(
    db: Session,
    customer_id: str,
    message: str,
    case_id: str,
    intent: str | None = None,
) -> dict:
    """Run ResolveAI's intent, evidence, validation, and action workflow.

    LLM output classifies the message and drafts policy answers. Order ownership,
    eligibility, and transaction execution remain controlled by backend code.
    """
    intent = intent or detect_intent(message)

    audit(
        db,
        case_id,
        "INTENT_DETECTED",
        {"intent": intent},
    )

    order_id = extract_order_id(message)
    evidence = []
    actions = []

    # General policy questions must not require an order number or enter a
    # transaction workflow.
    if intent in {"POLICY_QUESTION", "GENERAL"}:
        return _answer_policy_question(
            db=db,
            customer_id=customer_id,
            message=message,
            case_id=case_id,
            intent=intent,
        )

    # All order-related operations require an explicit order number.
    if intent in {
        "DAMAGED_PRODUCT",
        "REFUND",
        "RETURN",
        "DELIVERY",
        "CANCELLATION",
        "PAYMENT",
    }:
        if not order_id:
            return _result(
                intent=intent,
                status="WAITING_FOR_INFORMATION",
                response="Please provide your order number, for example ORD-48392.",
            )

        order = get_order(db, order_id)
        if not order:
            return _result(
                intent=intent,
                status="OPEN",
                response="I could not find that order.",
                escalation_reason="Order not found",
            )

        # Never expose or modify another customer's order.
        if order.customer_id != customer_id:
            return _result(
                intent=intent,
                status="ESCALATED",
                response="I could not verify that order under your customer account.",
                escalation_reason="Order does not belong to customer",
            )

        evidence.append(
            f"Order {order.order_id}: {order.status}, amount INR "
            f"{order.total_amount}, delivered {order.delivered_date}"
        )
        audit(db, case_id, "ORDER_RETRIEVED", {"order_id": order_id})

        # Retrieve policy evidence for order-related requests too. Policy text
        # informs the workflow but does not override deterministic checks below.
        policy = search_policy(message)
        evidence.append(policy)
        audit(db, case_id, "POLICY_RETRIEVED", {"policy": policy})

        # ---------------------------------------------------------
        # DAMAGED PRODUCT / REPLACEMENT
        # ---------------------------------------------------------
        if intent == "DAMAGED_PRODUCT":
            if not order.delivered_date:
                return _result(
                    intent=intent,
                    status="ESCALATED",
                    response=(
                        "The delivery information is incomplete, so I am "
                        "escalating this case to support."
                    ),
                    evidence=evidence,
                    actions=actions,
                    escalation_reason="Missing delivery date",
                )

            days_since_delivery = (datetime_today() - order.delivered_date).days
            if days_since_delivery < 0:
                return _result(
                    intent=intent,
                    status="ESCALATED",
                    response=(
                        "The recorded delivery date appears to be in the future. "
                        "A support representative needs to review this order."
                    ),
                    evidence=evidence,
                    actions=actions,
                    escalation_reason="Invalid delivery date",
                )

            if days_since_delivery > 7:
                audit(
                    db,
                    case_id,
                    "ELIGIBILITY_CHECK",
                    {"eligible": False, "reason": "Outside 7-day window"},
                )
                return _result(
                    intent=intent,
                    status="ESCALATED",
                    response=(
                        "The damaged-product report is outside the 7-day policy "
                        "window, so a support representative needs to review it."
                    ),
                    evidence=evidence,
                    actions=actions,
                    escalation_reason="Outside policy window",
                )

            if not order.evidence_received:
                audit(
                    db,
                    case_id,
                    "ELIGIBILITY_CHECK",
                    {
                        "eligible": True,
                        "evidence_required": True,
                        "evidence_received": False,
                    },
                )
                return _result(
                    intent=intent,
                    status="WAITING_FOR_INFORMATION",
                    response=(
                        "Your order appears eligible for a damaged-product "
                        "replacement. Please upload a photograph of the damaged "
                        "product so the replacement request can be reviewed."
                    ),
                    evidence=evidence,
                    actions=actions,
                )

            result = create_replacement(db, order)
            actions.append(str(result))
            audit(db, case_id, "REPLACEMENT_ACTION", result)

            if result.get("success"):
                return _result(
                    intent=intent,
                    status="RESOLVED",
                    response="Your replacement request has been created successfully.",
                    evidence=evidence,
                    actions=actions,
                )

            if "already exists" in result.get("message", "").lower():
                return _result(
                    intent=intent,
                    status="RESOLVED",
                    response=(
                        "A replacement request has already been recorded "
                        f"for your order. {result['message']}"
                    ),
                    evidence=evidence,
                    actions=actions,
                )

            return _result(
                intent=intent,
                status="ESCALATED",
                response=(
                    "I could not safely create the replacement request. A support "
                    "representative will review it."
                ),
                evidence=evidence,
                actions=actions,
                escalation_reason=result.get(
                    "message", "Replacement creation failed"
                ),
            )

        # ---------------------------------------------------------
        # REFUND
        # ---------------------------------------------------------
        if intent == "REFUND":
            payment = get_payment(db, order_id)
            if not payment:
                return _result(
                    intent=intent,
                    status="ESCALATED",
                    response=(
                        "Payment information is unavailable, so I am escalating "
                        "this case."
                    ),
                    evidence=evidence,
                    actions=actions,
                    escalation_reason="Missing payment record",
                )

            result = request_refund(
                db,
                order,
                payment,
                Decimal(str(order.total_amount)),
            )
            actions.append(str(result))
            audit(db, case_id, "REFUND_ACTION", result)

            if result.get("success"):
                return _result(
                    intent=intent,
                    status="RESOLVED",
                    response=(
                        f"Your refund request {result.get('refund_id', '')} "
                        "has been created successfully."
                    ),
                    evidence=evidence,
                    actions=actions,
                )

            return _result(
                intent=intent,
                status="ESCALATED",
                response=result.get("message", "The refund could not be processed."),
                evidence=evidence,
                actions=actions,
                escalation_reason=result.get("message", "Refund request failed"),
            )

        # ---------------------------------------------------------
        # RETURN
        # ---------------------------------------------------------
        if intent == "RETURN":
            result = create_return(db, order, "CUSTOMER_RETURN")
            actions.append(str(result))
            audit(db, case_id, "RETURN_ACTION", result)

            if result.get("success"):
                return _result(
                    intent=intent,
                    status="RESOLVED",
                    response=(
                        f"Your return request {result.get('return_id', '')} "
                        "has been created successfully."
                    ),
                    evidence=evidence,
                    actions=actions,
                )

            return _result(
                intent=intent,
                status="ESCALATED",
                response=result.get("message", "The return could not be created."),
                evidence=evidence,
                actions=actions,
                escalation_reason=result.get("message", "Return request failed"),
            )

        # ---------------------------------------------------------
        # DELIVERY
        # ---------------------------------------------------------
        if intent == "DELIVERY":
            return _result(
                intent=intent,
                status="RESOLVED",
                response=f"Order {order.order_id} is currently {order.status}.",
                evidence=evidence,
                actions=actions,
            )

        # Cancellation and payment operations are not implemented in the
        # existing tools shown in this project, so do not claim they succeeded.
        return _result(
            intent=intent,
            status="ESCALATED",
            response=(
                "I found the order, but this request needs a support "
                "representative to review the available information."
            ),
            evidence=evidence,
            actions=actions,
            escalation_reason="Unsupported automated operation",
        )

    # Defensive fallback in case a future classifier category is added but
    # has not yet been wired into a specific workflow.
    return _answer_policy_question(
        db=db,
        customer_id=customer_id,
        message=message,
        case_id=case_id,
        intent="GENERAL",
    )
