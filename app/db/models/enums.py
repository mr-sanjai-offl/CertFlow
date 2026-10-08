import enum


class JobStatus(enum.StrEnum):
    """
    Represents the processing state of a bulk generation job.

    States:
      QUEUED: Job accepted and waiting for processing by the worker.
      PROCESSING: Worker is currently generating certificates for this job.
      COMPLETED: All recipients succeeded. Job is fully finished.
      COMPLETED_WITH_ERRORS: Processing finished but one or more recipients failed.
      FAILED: Job-level processing failed before successful completion (e.g., total crash).
    """

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class RecipientStatus(enum.StrEnum):
    """
    Represents the processing state of a single recipient inside a job.

    States:
      PENDING: Recipient is queued and waiting for generation.
      PROCESSING: Worker is actively generating this recipient's certificate.
      SUCCESS: Certificate was generated and saved successfully.
      FAILED: Generation failed after exhausting retries.
    """

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
