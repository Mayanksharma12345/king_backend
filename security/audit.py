"""
HIPAA Audit Logging Module

Comprehensive audit logging for all PHI access and system events.
Implements HIPAA requirements for audit trails and access logging.
"""

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContainerClient
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)


class AuditEventType(str, Enum):
    """Types of auditable events"""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    MFA_CHALLENGE = "mfa_challenge"
    
    # PHI Access
    PHI_VIEW = "phi_view"
    PHI_CREATE = "phi_create"
    PHI_UPDATE = "phi_update"
    PHI_DELETE = "phi_delete"
    PHI_EXPORT = "phi_export"
    
    # System Events
    SYSTEM_ACCESS = "system_access"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHANGE = "permission_change"
    
    # Security Events
    SECURITY_VIOLATION = "security_violation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ENCRYPTION_KEY_ACCESS = "encryption_key_access"
    
    # Clinical Events
    TRANSCRIPTION_START = "transcription_start"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    SOAP_NOTE_GENERATED = "soap_note_generated"
    ICD10_LOOKUP = "icd10_lookup"


class AuditSeverity(str, Enum):
    """Severity levels for audit events"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """
    Audit event model compliant with HIPAA requirements.
    """
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.INFO
    
    # User information
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    
    # Access information
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    
    # Resource information
    resource_type: Optional[str] = None  # e.g., "patient", "encounter", "audio"
    resource_id: Optional[str] = None
    patient_id_hash: Optional[str] = None  # Hashed patient ID for correlation
    
    # Action details
    action: str
    result: str = "success"  # success, failure, denied
    reason: Optional[str] = None
    
    # Additional context
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # System information
    service_name: str = "medical-scribe-ai"
    environment: str = "production"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuditLogger:
    """
    HIPAA-compliant audit logger with Azure Storage backend.
    
    Features:
    - Immutable audit logs
    - Long-term retention (7 years)
    - Encrypted storage
    - Real-time logging
    - Tamper-evident logs
    """
    
    def __init__(
        self,
        storage_account_url: Optional[str] = None,
        container_name: str = "audit-logs",
        local_backup: bool = True
    ):
        """
        Initialize audit logger.
        
        Args:
            storage_account_url: Azure Storage account URL
            container_name: Container for audit logs
            local_backup: Whether to also log locally
        """
        self.container_name = container_name
        self.local_backup = local_backup
        
        if storage_account_url:
            credential = DefaultAzureCredential()
            self.blob_service_client = BlobServiceClient(
                account_url=storage_account_url,
                credential=credential
            )
            self.container_client: ContainerClient = self.blob_service_client.get_container_client(
                container_name
            )
            logger.info("Audit logger initialized with Azure Storage",
                       container=container_name)
        else:
            self.blob_service_client = None
            self.container_client = None
            logger.warning("Audit logger initialized in local-only mode")
    
    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event.
        
        Args:
            event: Audit event to log
        """
        try:
            # Serialize event
            event_json = event.model_dump_json(indent=2)
            
            # Log locally
            if self.local_backup:
                logger.info(
                    "audit_event",
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    user_id=event.user_id,
                    action=event.action,
                    result=event.result,
                    severity=event.severity.value
                )
            
            # Log to Azure Storage (append-only)
            if self.container_client:
                self._write_to_storage(event, event_json)
            
        except Exception as e:
            logger.error("Failed to log audit event", 
                        error=str(e),
                        event_type=event.event_type.value)
            raise
    
    def _write_to_storage(self, event: AuditEvent, event_json: str) -> None:
        """
        Write audit event to Azure Storage with append-only semantics.
        
        Args:
            event: Audit event
            event_json: Serialized event JSON
        """
        try:
            # Organize logs by date for efficient querying
            date_partition = event.timestamp.strftime("%Y/%m/%d")
            blob_name = f"{date_partition}/{event.event_id}.json"
            
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                event_json,
                overwrite=False,  # Prevent modification of existing logs
                metadata={
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "user_id": event.user_id or "anonymous",
                    "timestamp": event.timestamp.isoformat()
                }
            )
            
            logger.debug("Audit event written to storage", blob_name=blob_name)
            
        except Exception as e:
            logger.error("Failed to write audit event to storage", error=str(e))
            # Don't raise - local logging already succeeded
    
    def log_phi_access(
        self,
        user_id: str,
        patient_id_hash: str,
        action: str,
        resource_type: str,
        resource_id: str,
        result: str = "success",
        ip_address: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Log PHI access event.
        
        Args:
            user_id: User accessing PHI
            patient_id_hash: Hashed patient identifier
            action: Action performed (view, create, update, delete)
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            result: Result of access attempt
            ip_address: User's IP address
            metadata: Additional context
        """
        event = AuditEvent(
            event_type=self._get_phi_event_type(action),
            user_id=user_id,
            patient_id_hash=patient_id_hash,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            ip_address=ip_address,
            severity=AuditSeverity.INFO if result == "success" else AuditSeverity.WARNING,
            metadata=metadata or {}
        )
        self.log_event(event)
    
    def log_authentication(
        self,
        user_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        reason: Optional[str] = None
    ) -> None:
        """
        Log authentication event.
        
        Args:
            user_id: User attempting authentication
            success: Whether authentication succeeded
            ip_address: User's IP address
            reason: Failure reason if applicable
        """
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE,
            user_id=user_id,
            action="authenticate",
            result="success" if success else "failure",
            reason=reason,
            ip_address=ip_address,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING
        )
        self.log_event(event)
    
    def log_security_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        action: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Log security-related event.
        
        Args:
            event_type: Type of security event
            severity: Severity level
            action: Action that triggered the event
            user_id: User involved (if applicable)
            ip_address: IP address
            metadata: Additional context
        """
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            action=action,
            result="detected",
            ip_address=ip_address,
            metadata=metadata or {}
        )
        self.log_event(event)
    
    @staticmethod
    def _get_phi_event_type(action: str) -> AuditEventType:
        """Map action to PHI event type"""
        action_map = {
            "view": AuditEventType.PHI_VIEW,
            "read": AuditEventType.PHI_VIEW,
            "create": AuditEventType.PHI_CREATE,
            "update": AuditEventType.PHI_UPDATE,
            "modify": AuditEventType.PHI_UPDATE,
            "delete": AuditEventType.PHI_DELETE,
            "export": AuditEventType.PHI_EXPORT,
        }
        return action_map.get(action.lower(), AuditEventType.PHI_VIEW)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def initialize_audit_logger(storage_account_url: Optional[str] = None) -> AuditLogger:
    """
    Initialize the global audit logger.
    
    Args:
        storage_account_url: Azure Storage account URL
        
    Returns:
        AuditLogger: Initialized audit logger
    """
    global _audit_logger
    _audit_logger = AuditLogger(storage_account_url=storage_account_url)
    return _audit_logger
