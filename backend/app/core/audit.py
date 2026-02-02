"""
Audit Logging Module
Provides structured audit trail for security-critical operations
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request
    Handles X-Forwarded-For for proxy scenarios
    """
    # Check X-Forwarded-For header (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP in chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (nginx proxy)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"


def audit_log(
    action: str,
    user_id: int,
    resource_type: str,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    request: Optional[Request] = None
):
    """
    Log security-critical actions in structured format

    Args:
        action: Action performed (e.g., "user_created", "absence_approved")
        user_id: ID of user performing the action
        resource_type: Type of resource affected (e.g., "user", "absence", "attachment")
        resource_id: ID of affected resource (if applicable)
        details: Additional context (e.g., old/new values, status changes)
        ip_address: Client IP address (if not providing request)
        request: FastAPI Request object (for automatic IP extraction)

    Example:
        audit_log(
            action="absence_approved",
            user_id=current_user.id,
            resource_type="absence",
            resource_id=absence.id,
            details={"old_status": "submitted", "new_status": "approved"},
            request=request
        )
    """
    # Get IP address from request if not provided
    if ip_address is None and request is not None:
        ip_address = get_client_ip(request)
    elif ip_address is None:
        ip_address = "unknown"

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "user_id": user_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": ip_address
    }

    # Log as JSON for easy parsing/ingestion into SIEM systems
    logger.info(f"AUDIT: {json.dumps(log_entry)}")


# Convenience functions for common audit events

def audit_user_created(user_id: int, created_by: int, details: Dict[str, Any], request: Request):
    """Audit log for user creation"""
    audit_log("user_created", created_by, "user", user_id, details, request=request)


def audit_user_updated(user_id: int, updated_by: int, details: Dict[str, Any], request: Request):
    """Audit log for user updates (including role changes)"""
    audit_log("user_updated", updated_by, "user", user_id, details, request=request)


def audit_absence_created(absence_id: int, user_id: int, details: Dict[str, Any], request: Request):
    """Audit log for absence creation"""
    audit_log("absence_created", user_id, "absence", absence_id, details, request=request)


def audit_absence_approved(absence_id: int, approver_id: int, details: Dict[str, Any], request: Request):
    """Audit log for absence approval"""
    audit_log("absence_approved", approver_id, "absence", absence_id, details, request=request)


def audit_absence_completed(absence_id: int, completer_id: int, details: Dict[str, Any], request: Request):
    """Audit log for absence completion"""
    audit_log("absence_completed", completer_id, "absence", absence_id, details, request=request)


def audit_file_uploaded(attachment_id: int, user_id: int, details: Dict[str, Any], request: Request):
    """Audit log for file upload"""
    audit_log("file_uploaded", user_id, "attachment", attachment_id, details, request=request)


def audit_file_deleted(attachment_id: int, user_id: int, details: Dict[str, Any], request: Request):
    """Audit log for file deletion"""
    audit_log("file_deleted", user_id, "attachment", attachment_id, details, request=request)


def audit_role_changed(user_id: int, changed_by: int, old_role: str, new_role: str, request: Request):
    """Audit log for role changes (critical security event)"""
    audit_log(
        "role_changed",
        changed_by,
        "user",
        user_id,
        {"old_role": old_role, "new_role": new_role},
        request=request
    )
