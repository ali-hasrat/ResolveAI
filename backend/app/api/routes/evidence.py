from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.models import (
    Customer,
    Order,
    SupportCase,
)

from app.agent.agent import run_agent


router = APIRouter(
    prefix="/evidence",
    tags=["Evidence"],
)


# ============================================================
# FILE STORAGE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

UPLOAD_DIR = (
    BASE_DIR
    / "data"
    / "evidence"
)

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# FILE VALIDATION
# ============================================================

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


# ============================================================
# UPLOAD EVIDENCE
# ============================================================

@router.post("/upload")
async def upload_evidence(
    customer_id: str = Form(...),
    order_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload photographic evidence for a damaged product.

    After successful validation:

        order.evidence_received = True

    The original support case is then resumed automatically.
    """

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # 1. Validate file type
        # ----------------------------------------------------

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid file type. Please upload "
                    "a JPG, PNG, or WEBP image."
                ),
            )

        # ----------------------------------------------------
        # 2. Find customer
        # ----------------------------------------------------

        customer = db.scalar(
            select(Customer).where(
                Customer.customer_id == customer_id
            )
        )

        if not customer:
            raise HTTPException(
                status_code=404,
                detail="Customer not found.",
            )

        # ----------------------------------------------------
        # 3. Find order
        # ----------------------------------------------------

        order = db.scalar(
            select(Order).where(
                Order.order_id == order_id
            )
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        # ----------------------------------------------------
        # 4. Verify ownership
        # ----------------------------------------------------

        if order.customer_id != customer.customer_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "This order does not belong to "
                    "the specified customer."
                ),
            )

        # ----------------------------------------------------
        # 5. Verify delivery
        # ----------------------------------------------------

        if order.status != "DELIVERED":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Evidence can only be submitted "
                    "for a delivered order."
                ),
            )

        # ----------------------------------------------------
        # 6. Read file
        # ----------------------------------------------------

        contents = await file.read()

        # ----------------------------------------------------
        # 7. Validate size
        # ----------------------------------------------------

        if len(contents) == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=(
                    "File is too large. Maximum allowed "
                    "size is 10 MB."
                ),
            )

        # ----------------------------------------------------
        # 8. Safe filename
        # ----------------------------------------------------

        extension = Path(
            file.filename or ""
        ).suffix.lower()

        if extension not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }:
            extension = ".jpg"

        filename = (
            f"{order.order_id}_"
            f"{uuid4().hex}"
            f"{extension}"
        )

        file_path = (
            UPLOAD_DIR / filename
        )

        # ----------------------------------------------------
        # 9. Save evidence
        # ----------------------------------------------------

        file_path.write_bytes(contents)

        # ----------------------------------------------------
        # 10. Update order
        # ----------------------------------------------------

        order.evidence_received = True

        db.commit()
        db.refresh(order)

        # ====================================================
        # 11. FIND EXISTING OPEN CASE
        # ====================================================

        existing_case = db.scalar(
            select(SupportCase)
            .where(
                SupportCase.customer_id
                == customer.customer_id,
                SupportCase.status
                == "WAITING_FOR_INFORMATION",
            )
            .order_by(
                SupportCase.created_at.desc()
            )
        )

        # ----------------------------------------------------
        # If no existing waiting case exists, we still
        # successfully accept the evidence.
        # ----------------------------------------------------

        if not existing_case:

            return {
                "success": True,
                "message": (
                    "Evidence uploaded successfully, "
                    "but no waiting support case was found."
                ),
                "customer_id": customer.customer_id,
                "order_id": order.order_id,
                "evidence_received": True,
                "filename": filename,
                "file_size": len(contents),
                "case_resumed": False,
            }

        # ====================================================
        # 12. RESUME RESOLVEAI
        # ====================================================

        result = run_agent(
            db=db,
            customer_id=customer.customer_id,
            message=existing_case.message,
            case_id=existing_case.case_id,
        )

        # ====================================================
        # 13. UPDATE CASE
        # ====================================================

        existing_case.status = result["status"]

        existing_case.resolution = (
            result["response"]
        )

        if result.get(
            "escalation_reason"
        ):
            existing_case.escalation_reason = (
                result["escalation_reason"]
            )

        db.commit()
        db.refresh(existing_case)

        # ====================================================
        # 14. RETURN FINAL RESULT
        # ====================================================

        return {
            "success": True,
            "message": (
                "Evidence uploaded and support case "
                "processed successfully."
            ),
            "customer_id": customer.customer_id,
            "order_id": order.order_id,
            "evidence_received": True,
            "filename": filename,
            "file_size": len(contents),
            "case_resumed": True,
            "case_id": existing_case.case_id,
            "case_status": result["status"],
            "intent": result["intent"],
            "response": result["response"],
            "evidence": result.get(
                "evidence",
                [],
            ),
            "actions": result.get(
                "actions",
                [],
            ),
            "escalation_reason": result.get(
                "escalation_reason"
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred while "
                "processing the evidence."
            ),
        ) from exc

    finally:
        db.close()