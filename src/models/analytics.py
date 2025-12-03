"""
Analytics and Reporting Data Models

Provides data structures for tracking and reporting system usage,
physician productivity, and compliance metrics.
"""

from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Types of reports available"""
    PHYSICIAN_PRODUCTIVITY = "physician_productivity"
    ENCOUNTER_SUMMARY = "encounter_summary"
    COMPLIANCE_AUDIT = "compliance_audit"
    USAGE_STATISTICS = "usage_statistics"
    BILLING_SUMMARY = "billing_summary"
    QUALITY_METRICS = "quality_metrics"


class PhysicianProductivityReport(BaseModel):
    """Physician productivity metrics"""
    physician_id: str
    physician_name: str
    date_range_start: date
    date_range_end: date
    
    # Encounter metrics
    total_encounters: int
    encounters_per_day: float
    average_encounter_duration: float  # minutes
    
    # Documentation metrics
    total_documentation_time: float  # minutes
    average_documentation_time: float  # minutes per encounter
    documentation_time_saved: float  # estimated time saved vs manual
    
    # Quality metrics
    notes_generated: int
    notes_edited: int
    edit_percentage: float
    average_note_completeness: float  # 0-100
    
    # ICD-10 coding
    total_codes_suggested: int
    codes_accepted: int
    codes_modified: int
    coding_accuracy_rate: float


class EncounterSummaryReport(BaseModel):
    """Summary of encounters over time period"""
    date_range_start: date
    date_range_end: date
    
    # Volume metrics
    total_encounters: int
    encounters_by_day: dict[str, int]  # date -> count
    encounters_by_physician: dict[str, int]  # physician_id -> count
    encounters_by_specialty: dict[str, int]
    
    # Chief complaints
    top_chief_complaints: List[tuple[str, int]]  # (complaint, count)
    
    # Diagnoses
    top_diagnoses: List[tuple[str, int]]  # (diagnosis, count)
    top_icd10_codes: List[tuple[str, int]]  # (code, count)
    
    # Time metrics
    average_encounter_duration: float
    peak_hours: List[tuple[int, int]]  # (hour, count)


class ComplianceAuditReport(BaseModel):
    """HIPAA compliance audit report"""
    date_range_start: date
    date_range_end: date
    
    # Access tracking
    total_phi_access_events: int
    unique_users_accessed: int
    unauthorized_access_attempts: int
    
    # Access by type
    access_by_event_type: dict[str, int]
    access_by_user: dict[str, int]
    
    # Security events
    failed_login_attempts: int
    mfa_challenges: int
    security_violations: int
    
    # Encryption compliance
    encrypted_records_percentage: float
    encryption_key_rotations: int
    
    # Audit log health
    audit_logs_complete: bool
    audit_log_gaps: List[str]  # dates with missing logs
    
    # Compliance score
    overall_compliance_score: float  # 0-100
    compliance_issues: List[str]
    recommendations: List[str]


class UsageStatisticsReport(BaseModel):
    """System usage statistics"""
    date_range_start: date
    date_range_end: date
    
    # User activity
    total_active_users: int
    daily_active_users: float  # average
    new_users: int
    
    # Feature usage
    transcriptions_performed: int
    soap_notes_generated: int
    encounters_saved: int
    
    # System performance
    average_transcription_time: float  # seconds
    average_soap_generation_time: float  # seconds
    system_uptime_percentage: float
    
    # API usage
    total_api_calls: int
    api_calls_by_endpoint: dict[str, int]
    average_response_time: float  # ms
    error_rate: float  # percentage


class BillingSummaryReport(BaseModel):
    """Billing and revenue summary"""
    date_range_start: date
    date_range_end: date
    
    # Encounter billing
    total_billable_encounters: int
    encounters_by_cpt_code: dict[str, int]
    
    # Documentation completeness
    complete_documentation_percentage: float
    incomplete_encounters: int
    missing_required_fields: dict[str, int]
    
    # Coding metrics
    total_diagnosis_codes: int
    average_codes_per_encounter: float
    
    # Time savings (cost savings)
    estimated_time_saved_hours: float
    estimated_cost_savings: float  # based on physician hourly rate


class QualityMetricsReport(BaseModel):
    """Clinical documentation quality metrics"""
    date_range_start: date
    date_range_end: date
    
    # Note completeness
    average_note_completeness: float  # 0-100
    notes_with_all_soap_sections: int
    notes_missing_sections: int
    
    # Clinical detail
    average_subjective_length: int  # words
    average_objective_length: int
    average_assessment_length: int
    average_plan_length: int
    
    # Accuracy metrics
    transcription_accuracy_rate: float  # based on manual review
    icd10_coding_accuracy: float
    
    # Edit frequency
    notes_edited_after_generation: int
    average_edits_per_note: float
    
    # Compliance with guidelines
    notes_meeting_standards: int
    quality_score: float  # 0-100


class DashboardMetrics(BaseModel):
    """Real-time dashboard metrics"""
    
    # Today's activity
    encounters_today: int
    active_users_now: int
    transcriptions_in_progress: int
    
    # This week
    encounters_this_week: int
    average_encounters_per_day: float
    
    # This month
    encounters_this_month: int
    month_over_month_growth: float  # percentage
    
    # System health
    system_status: str  # "healthy", "degraded", "down"
    api_response_time: float  # ms
    error_rate: float  # percentage
    
    # Recent activity
    recent_encounters: List[dict]  # Last 10 encounters (sanitized)
    
    # Alerts
    active_alerts: List[dict]  # System alerts and notifications


class ReportRequest(BaseModel):
    """Request for generating a report"""
    report_type: ReportType
    date_range_start: date
    date_range_end: date
    
    # Filters
    physician_ids: Optional[List[str]] = None
    department: Optional[str] = None
    specialty: Optional[str] = None
    
    # Output options
    format: str = Field(default="json", pattern="^(json|csv|pdf)$")
    include_details: bool = True


class ReportResponse(BaseModel):
    """Response containing generated report"""
    report_id: str
    report_type: ReportType
    generated_at: datetime
    generated_by: str
    
    # Report data
    data: dict  # Contains the specific report type data
    
    # Metadata
    record_count: int
    date_range_start: date
    date_range_end: date
    
    # Download options
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
