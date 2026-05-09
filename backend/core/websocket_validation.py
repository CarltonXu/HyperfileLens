"""
WebSocket message validation module for HyperFileLens.

This module provides validation functions for WebSocket messages
to ensure data integrity and security.
"""

import re
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum

from django.core.validators import validate_email, URLValidator
from django.core.exceptions import ValidationError
import jsonschema


class ValidationSeverity(Enum):
    """Severity of validation error."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationError:
    """Validation error details."""
    field: str
    message: str
    severity: ValidationSeverity
    code: str


class ValidationResult:
    """Result of message validation."""

    def __init__(self, valid: bool, errors: List[ValidationError] = None):
        self.valid = valid
        self.errors = errors or []

    def add_error(self, field: str, message: str, severity: ValidationSeverity = ValidationSeverity.ERROR, code: str = "invalid"):
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, severity, code))
        self.valid = severity in [ValidationSeverity.INFO, ValidationSeverity.WARNING]

    def get_errors_by_severity(self, severity: ValidationSeverity) -> List[ValidationError]:
        """Get errors filtered by severity."""
        return [e for e in self.errors if e.severity == severity]

    def has_critical_errors(self) -> bool:
        """Check if result has critical errors."""
        return any(e.severity == ValidationSeverity.CRITICAL for e in self.errors)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'valid': self.valid,
            'errors': [
                {
                    'field': e.field,
                    'message': e.message,
                    'severity': e.severity.value,
                    'code': e.code
                }
                for e in self.errors
            ]
        }


# Message type schemas
MESSAGE_SCHEMAS = {
    # Heartbeat message
    'heartbeat': {
        'type': 'object',
        'required': ['type', 'payload'],
        'properties': {
            'type': {'type': 'string', 'enum': ['heartbeat']},
            'id': {'type': 'string'},
            'payload': {
                'type': 'object',
                'required': ['node_id', 'status'],
                'properties': {
                    'node_id': {'type': 'string', 'minLength': 1},
                    'status': {'type': 'string', 'enum': ['online', 'offline']},
                    'metrics': {
                        'type': 'object',
                        'properties': {
                            'cpu_usage': {'type': 'number', 'minimum': 0, 'maximum': 100},
                            'memory_usage': {'type': 'number', 'minimum': 0, 'maximum': 100},
                            'disk_usage': {'type': 'number', 'minimum': 0, 'maximum': 100},
                            'network_bytes_sent': {'type': 'number', 'minimum': 0},
                            'network_bytes_recv': {'type': 'number', 'minimum': 0},
                        }
                    }
                }
            }
        }
    },

    # Task start message
    'task_start': {
        'type': 'object',
        'required': ['type', 'payload'],
        'properties': {
            'type': {'type': 'string', 'enum': ['task_start']},
            'id': {'type': 'string'},
            'payload': {
                'type': 'object',
                'required': ['task_id', 'task_type'],
                'properties': {
                    'task_id': {'type': 'string', 'minLength': 1},
                    'task_type': {'type': 'string', 'enum': ['backup', 'restore', 'mount', 'list_snapshots']},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                }
            }
        }
    },

    # Task progress message
    'task_progress': {
        'type': 'object',
        'required': ['type', 'payload'],
        'properties': {
            'type': {'type': 'string', 'enum': ['task_progress']},
            'id': {'type': 'string'},
            'payload': {
                'type': 'object',
                'required': ['task_id', 'progress'],
                'properties': {
                    'task_id': {'type': 'string', 'minLength': 1},
                    'task_type': {'type': 'string'},
                    'status': {'type': 'string', 'enum': ['running', 'completed', 'failed', 'cancelled']},
                    'progress': {'type': 'integer', 'minimum': 0, 'maximum': 100},
                    'message': {'type': 'string'},
                    'current_file': {'type': 'string'},
                    'total_files': {'type': 'integer', 'minimum': 0},
                    'processed_files': {'type': 'integer', 'minimum': 0},
                    'total_bytes': {'type': 'integer', 'minimum': 0},
                    'processed_bytes': {'type': 'integer', 'minimum': 0},
                    'speed_mbps': {'type': 'number', 'minimum': 0},
                    'eta': {'type': 'string'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                }
            }
        }
    },

    # Task complete message
    'task_complete': {
        'type': 'object',
        'required': ['type', 'payload'],
        'properties': {
            'type': {'type': 'string', 'enum': ['task_complete']},
            'id': {'type': 'string'},
            'payload': {
                'type': 'object',
                'required': ['task_id', 'success'],
                'properties': {
                    'task_id': {'type': 'string', 'minLength': 1},
                    'success': {'type': 'boolean'},
                    'result': {'type': 'object'},
                    'error': {'type': 'string'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                }
            }
        }
    },

    # Error message
    'error': {
        'type': 'object',
        'required': ['type', 'payload'],
        'properties': {
            'type': {'type': 'string', 'enum': ['error']},
            'id': {'type': 'string'},
            'payload': {
                'type': 'object',
                'required': ['error'],
                'properties': {
                    'error': {'type': 'string', 'minLength': 1},
                    'task_id': {'type': 'string'},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                }
            }
        }
    },
}


class WebSocketMessageValidator:
    """Validator for WebSocket messages."""

    def __init__(self):
        self.schemas = MESSAGE_SCHEMAS

    def validate(self, message: Dict[str, Any]) -> ValidationResult:
        """
        Validate a WebSocket message.

        Args:
            message: Message dictionary

        Returns:
            ValidationResult with validation errors if any
        """
        result = ValidationResult(valid=True)

        # Check if message is a dictionary
        if not isinstance(message, dict):
            result.add_error(
                'message',
                'Message must be a dictionary',
                ValidationSeverity.CRITICAL,
                'invalid_type'
            )
            return result

        # Check required fields
        if 'type' not in message:
            result.add_error(
                'type',
                'Message type is required',
                ValidationSeverity.CRITICAL,
                'missing_field'
            )
        else:
            # Validate message type
            message_type = message.get('type')
            if message_type not in self.schemas:
                result.add_error(
                    'type',
                    f'Unknown message type: {message_type}',
                    ValidationSeverity.ERROR,
                    'invalid_type'
                )

        # Check payload field
        if 'payload' not in message:
            result.add_error(
                'payload',
                'Message payload is required',
                ValidationSeverity.CRITICAL,
                'missing_field'
            )
        elif not isinstance(message.get('payload'), dict):
            result.add_error(
                'payload',
                'Payload must be a dictionary',
                ValidationSeverity.ERROR,
                'invalid_type'
            )

        # Validate against schema if available
        if message.get('type') in self.schemas:
            schema = self.schemas[message['type']]
            self._validate_schema(message, schema, result)

        # Validate message ID if present
        if 'id' in message:
            self._validate_message_id(message['id'], result)

        # Validate payload content
        if 'payload' in message and isinstance(message['payload'], dict):
            self._validate_payload(message['payload'], message.get('type'), result)

        return result

    def _validate_schema(self, message: Dict[str, Any], schema: Dict[str, Any], result: ValidationResult):
        """Validate message against JSON schema."""
        try:
            jsonschema.validate(message, schema)
        except jsonschema.ValidationError as e:
            field = '.'.join(str(p) for p in e.path) if e.path else 'message'
            result.add_error(
                field,
                e.message,
                ValidationSeverity.ERROR,
                'schema_validation'
            )

    def _validate_message_id(self, message_id: Any, result: ValidationResult):
        """Validate message ID format."""
        if not isinstance(message_id, str):
            result.add_error(
                'id',
                'Message ID must be a string',
                ValidationSeverity.WARNING,
                'invalid_format'
            )
        elif len(message_id) == 0:
            result.add_error(
                'id',
                'Message ID cannot be empty',
                ValidationSeverity.WARNING,
                'invalid_format'
            )

    def _validate_payload(self, payload: Dict[str, Any], message_type: str, result: ValidationResult):
        """Validate payload content based on message type."""
        if message_type == 'heartbeat':
            self._validate_heartbeat_payload(payload, result)
        elif message_type == 'task_progress':
            self._validate_task_progress_payload(payload, result)
        elif message_type == 'task_start':
            self._validate_task_start_payload(payload, result)

    def _validate_heartbeat_payload(self, payload: Dict[str, Any], result: ValidationResult):
        """Validate heartbeat payload."""
        # Validate metrics if present
        if 'metrics' in payload:
            metrics = payload['metrics']
            if not isinstance(metrics, dict):
                result.add_error(
                    'payload.metrics',
                    'Metrics must be a dictionary',
                    ValidationSeverity.WARNING,
                    'invalid_type'
                )
                return

            # Validate metric values
            for key, value in metrics.items():
                if key in ['cpu_usage', 'memory_usage', 'disk_usage']:
                    if not isinstance(value, (int, float)):
                        result.add_error(
                            f'payload.metrics.{key}',
                            f'{key} must be a number',
                            ValidationSeverity.WARNING,
                            'invalid_type'
                        )
                    elif value < 0 or value > 100:
                        result.add_error(
                            f'payload.metrics.{key}',
                            f'{key} must be between 0 and 100',
                            ValidationSeverity.WARNING,
                            'out_of_range'
                        )

    def _validate_task_progress_payload(self, payload: Dict[str, Any], result: ValidationResult):
        """Validate task progress payload."""
        # Validate progress value
        if 'progress' in payload:
            progress = payload['progress']
            if not isinstance(progress, int):
                result.add_error(
                    'payload.progress',
                    'Progress must be an integer',
                    ValidationSeverity.WARNING,
                    'invalid_type'
                )
            elif progress < 0 or progress > 100:
                result.add_error(
                    'payload.progress',
                    'Progress must be between 0 and 100',
                    ValidationSeverity.WARNING,
                    'out_of_range'
                )

        # Validate file counts
        for field in ['total_files', 'processed_files']:
            if field in payload:
                value = payload[field]
                if not isinstance(value, int) or value < 0:
                    result.add_error(
                        f'payload.{field}',
                        f'{field} must be a non-negative integer',
                        ValidationSeverity.WARNING,
                        'invalid_value'
                    )

        # Validate byte counts
        for field in ['total_bytes', 'processed_bytes']:
            if field in payload:
                value = payload[field]
                if not isinstance(value, int) or value < 0:
                    result.add_error(
                        f'payload.{field}',
                        f'{field} must be a non-negative integer',
                        ValidationSeverity.WARNING,
                        'invalid_value'
                    )

        # Validate speed
        if 'speed_mbps' in payload:
            speed = payload['speed_mbps']
            if not isinstance(speed, (int, float)) or speed < 0:
                result.add_error(
                    'payload.speed_mbps',
                    'Speed must be a non-negative number',
                    ValidationSeverity.WARNING,
                    'invalid_value'
                )

    def _validate_task_start_payload(self, payload: Dict[str, Any], result: ValidationResult):
        """Validate task start payload."""
        # Validate task type
        if 'task_type' in payload:
            valid_types = ['backup', 'restore', 'mount', 'list_snapshots']
            if payload['task_type'] not in valid_types:
                result.add_error(
                    'payload.task_type',
                    f'Invalid task type. Must be one of: {", ".join(valid_types)}',
                    ValidationSeverity.ERROR,
                    'invalid_type'
                )

        # Validate task ID format
        if 'task_id' in payload:
            task_id = payload['task_id']
            if not isinstance(task_id, str) or len(task_id) == 0:
                result.add_error(
                    'payload.task_id',
                    'Task ID must be a non-empty string',
                    ValidationSeverity.ERROR,
                    'invalid_format'
                )


# Global validator instance
validator = WebSocketMessageValidator()


def validate_websocket_message(message: Dict[str, Any]) -> ValidationResult:
    """
    Validate a WebSocket message.

    Args:
        message: Message dictionary

    Returns:
        ValidationResult
    """
    return validator.validate(message)


def validate_and_log(message: Dict[str, Any], logger=None) -> Tuple[bool, ValidationResult]:
    """
    Validate a message and log any errors.

    Args:
        message: Message dictionary
        logger: Optional logger instance

    Returns:
        Tuple of (is_valid, ValidationResult)
    """
    result = validate_websocket_message(message)

    if not result.valid:
        if logger:
            for error in result.errors:
                if error.severity == ValidationSeverity.CRITICAL:
                    logger.error(
                        f"WebSocket message validation failed: {error.message}",
                        extra={
                            'field': error.field,
                            'code': error.code
                        }
                    )
                elif error.severity == ValidationSeverity.ERROR:
                    logger.warning(
                        f"WebSocket message validation error: {error.message}",
                        extra={
                            'field': error.field,
                            'code': error.code
                        }
                    )
                else:
                    logger.info(
                        f"WebSocket message validation info: {error.message}",
                        extra={
                            'field': error.field,
                            'code': error.code
                        }
                    )

    return result.valid, result
