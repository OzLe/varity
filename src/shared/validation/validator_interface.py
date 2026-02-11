"""
Validator interface for standardized validation.

This module defines the interface for validation implementations,
ensuring consistent validation behavior across the application.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic

T = TypeVar('T')


class ValidationSeverity(Enum):
    """Validation severity levels."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    """
    Validation issue information.
    
    This class represents a single validation issue,
    including its severity, message, and context.
    """
    
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    value: Any = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult(Generic[T]):
    """
    Validation result.
    
    This class represents the result of a validation operation,
    including any issues found and the validated data.
    """
    
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    data: Optional[T] = None
    
    def add_issue(
        self,
        severity: ValidationSeverity,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        **context: Any
    ) -> None:
        """
        Add validation issue.
        
        Args:
            severity: Issue severity
            message: Issue message
            field: Optional field name
            value: Optional invalid value
            **context: Additional context
        """
        self.issues.append(
            ValidationIssue(
                severity=severity,
                message=message,
                field=field,
                value=value,
                context=context
            )
        )
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False
    
    def merge(self, other: 'ValidationResult[T]') -> 'ValidationResult[T]':
        """
        Merge with another validation result.
        
        Args:
            other: Result to merge with
            
        Returns:
            ValidationResult[T]: Merged result
        """
        merged = ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            data=self.data or other.data
        )
        merged.issues.extend(self.issues)
        merged.issues.extend(other.issues)
        return merged
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "is_valid": self.is_valid,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "field": issue.field,
                    "value": issue.value,
                    "context": issue.context
                }
                for issue in self.issues
            ],
            "data": self.data
        }


class ValidatorInterface(ABC, Generic[T]):
    """
    Interface for validation implementations.
    
    This abstract class defines the contract that all validation
    implementations must follow to ensure consistent validation
    behavior across the application.
    """
    
    @abstractmethod
    def validate(self, data: T) -> ValidationResult[T]:
        """
        Validate data.
        
        Args:
            data: Data to validate
            
        Returns:
            ValidationResult[T]: Validation result
        """
        pass
    
    @abstractmethod
    def validate_field(
        self,
        field: str,
        value: Any,
        data: T
    ) -> ValidationResult[T]:
        """
        Validate specific field.
        
        Args:
            field: Field name
            value: Field value
            data: Complete data object
            
        Returns:
            ValidationResult[T]: Validation result
        """
        pass
    
    @abstractmethod
    def get_rules(self) -> Dict[str, List[Any]]:
        """
        Get validation rules.
        
        Returns:
            Dict[str, List[Any]]: Validation rules
        """
        pass
    
    @abstractmethod
    def add_rule(
        self,
        field: str,
        rule: Any,
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ) -> None:
        """
        Add validation rule.
        
        Args:
            field: Field to validate
            rule: Validation rule
            severity: Rule severity
        """
        pass
    
    @abstractmethod
    def remove_rule(self, field: str, rule: Any) -> None:
        """
        Remove validation rule.
        
        Args:
            field: Field name
            rule: Rule to remove
        """
        pass
    
    @abstractmethod
    def clear_rules(self) -> None:
        """Clear all validation rules."""
        pass 