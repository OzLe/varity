"""
Validation rules for standardized validation.

This module provides reusable validation rules that can be
composed to create complex validation logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Pattern, Type, Union
import re
from datetime import datetime
from enum import Enum

from .validator_interface import ValidationSeverity


class ValidationRule(ABC):
    """
    Base class for validation rules.
    
    This abstract class defines the interface for validation
    rules and provides common functionality.
    """
    
    def __init__(
        self,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Initialize validation rule.
        
        Args:
            message: Error message
            severity: Rule severity
        """
        self.message = message
        self.severity = severity
    
    @abstractmethod
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate value.
        
        Args:
            value: Value to validate
            context: Optional validation context
            
        Returns:
            bool: Whether value is valid
        """
        pass


class RequiredRule(ValidationRule):
    """Rule that requires a value to be present."""
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value is present."""
        return value is not None and value != ""


class TypeRule(ValidationRule):
    """Rule that validates value type."""
    
    def __init__(
        self,
        message: str,
        expected_type: Type,
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Initialize type rule.
        
        Args:
            message: Error message
            expected_type: Expected value type
            severity: Rule severity
        """
        super().__init__(message, severity)
        self.expected_type = expected_type
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value is of expected type."""
        return isinstance(value, self.expected_type)


class RangeRule(ValidationRule):
    """Rule that validates value range."""
    
    def __init__(
        self,
        message: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Initialize range rule.
        
        Args:
            message: Error message
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            severity: Rule severity
        """
        super().__init__(message, severity)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value is within range."""
        if not isinstance(value, (int, float)):
            return False
        
        if self.min_value is not None and value < self.min_value:
            return False
        
        if self.max_value is not None and value > self.max_value:
            return False
        
        return True


class LengthRule(ValidationRule):
    """Rule that validates value length."""
    
    def __init__(
        self,
        message: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Initialize length rule.
        
        Args:
            message: Error message
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            severity: Rule severity
        """
        super().__init__(message, severity)
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value length is within range."""
        if not hasattr(value, "__len__"):
            return False
        
        length = len(value)
        
        if self.min_length is not None and length < self.min_length:
            return False
        
        if self.max_length is not None and length > self.max_length:
            return False
        
        return True


class PatternRule(ValidationRule):
    """Rule that validates value against pattern."""
    
    def __init__(
        self,
        message: str,
        pattern: Union[str, Pattern],
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Initialize pattern rule.
        
        Args:
            message: Error message
            pattern: Regular expression pattern
            severity: Rule severity
        """
        super().__init__(message, severity)
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value matches pattern."""
        if not isinstance(value, str):
            return False
        
        return bool(self.pattern.match(value))


class EnumRule(ValidationRule):
    """Rule that validates value against enum."""
    
    def __init__(
        self,
        message: str,
        enum_class: Type[Enum],
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Initialize enum rule.
        
        Args:
            message: Error message
            enum_class: Enum class to validate against
            severity: Rule severity
        """
        super().__init__(message, severity)
        self.enum_class = enum_class
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value is valid enum value."""
        try:
            if isinstance(value, str):
                self.enum_class(value)
            elif isinstance(value, self.enum_class):
                return True
            return False
        except ValueError:
            return False


class DateRule(ValidationRule):
    """Rule that validates date format."""
    
    def __init__(
        self,
        message: str,
        format: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Initialize date rule.
        
        Args:
            message: Error message
            format: Expected date format
            severity: Rule severity
        """
        super().__init__(message, severity)
        self.format = format
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value is valid date."""
        if isinstance(value, datetime):
            return True
        
        if not isinstance(value, str):
            return False
        
        try:
            datetime.strptime(value, self.format)
            return True
        except ValueError:
            return False


class CustomRule(ValidationRule):
    """Rule that uses custom validation function."""
    
    def __init__(
        self,
        message: str,
        validator: Callable[[Any, Optional[Dict[str, Any]]], bool],
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ):
        """
        Initialize custom rule.
        
        Args:
            message: Error message
            validator: Validation function
            severity: Rule severity
        """
        super().__init__(message, severity)
        self.validator = validator
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value is valid using custom validator."""
        return self.validator(value, context)


class CompositeRule(ValidationRule):
    """Rule that combines multiple rules."""
    
    def __init__(
        self,
        message: str,
        rules: List[ValidationRule],
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        require_all: bool = True
    ):
        """
        Initialize composite rule.
        
        Args:
            message: Error message
            rules: List of rules to combine
            severity: Rule severity
            require_all: Whether all rules must pass
        """
        super().__init__(message, severity)
        self.rules = rules
        self.require_all = require_all
    
    def validate(
        self,
        value: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if value is valid according to combined rules."""
        results = [
            rule.validate(value, context)
            for rule in self.rules
        ]
        
        if self.require_all:
            return all(results)
        return any(results) 