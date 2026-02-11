"""
Validation engine for orchestrating validation rules.

This module provides a validation engine that manages and executes
validation rules against data structures.
"""

from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field

from .validator_interface import ValidationIssue, ValidationResult, ValidationSeverity
from .validation_rules import ValidationRule, CompositeRule


@dataclass
class ValidationContext:
    """Context for validation operations."""
    
    data: Dict[str, Any]
    parent_path: str = ""
    custom_context: Dict[str, Any] = field(default_factory=dict)


class ValidationEngine:
    """
    Engine for orchestrating validation rules.
    
    This class manages validation rules and executes them against
    data structures, providing detailed validation results.
    """
    
    def __init__(self):
        """Initialize validation engine."""
        self._rules: Dict[str, List[ValidationRule]] = {}
    
    def add_rule(
        self,
        field_path: str,
        rule: ValidationRule
    ) -> None:
        """
        Add validation rule for a field.
        
        Args:
            field_path: Path to field in dot notation
            rule: Validation rule to add
        """
        if field_path not in self._rules:
            self._rules[field_path] = []
        self._rules[field_path].append(rule)
    
    def add_rules(
        self,
        field_path: str,
        rules: List[ValidationRule]
    ) -> None:
        """
        Add multiple validation rules for a field.
        
        Args:
            field_path: Path to field in dot notation
            rules: List of validation rules to add
        """
        if field_path not in self._rules:
            self._rules[field_path] = []
        self._rules[field_path].extend(rules)
    
    def remove_rule(
        self,
        field_path: str,
        rule: ValidationRule
    ) -> None:
        """
        Remove validation rule for a field.
        
        Args:
            field_path: Path to field in dot notation
            rule: Validation rule to remove
        """
        if field_path in self._rules:
            self._rules[field_path].remove(rule)
            if not self._rules[field_path]:
                del self._rules[field_path]
    
    def clear_rules(self, field_path: Optional[str] = None) -> None:
        """
        Clear validation rules.
        
        Args:
            field_path: Optional path to clear rules for
        """
        if field_path:
            self._rules.pop(field_path, None)
        else:
            self._rules.clear()
    
    def validate(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate data against all rules.
        
        Args:
            data: Data to validate
            context: Optional validation context
            
        Returns:
            ValidationResult: Validation result
        """
        validation_context = ValidationContext(
            data=data,
            custom_context=context or {}
        )
        
        issues: List[ValidationIssue] = []
        
        for field_path, rules in self._rules.items():
            value = self._get_value(data, field_path)
            field_issues = self._validate_field(
                value,
                rules,
                field_path,
                validation_context
            )
            issues.extend(field_issues)
        
        return ValidationResult(issues=issues)
    
    def _validate_field(
        self,
        value: Any,
        rules: List[ValidationRule],
        field_path: str,
        context: ValidationContext
    ) -> List[ValidationIssue]:
        """
        Validate field against rules.
        
        Args:
            value: Value to validate
            rules: Rules to validate against
            field_path: Path to field
            context: Validation context
            
        Returns:
            List[ValidationIssue]: Validation issues
        """
        issues: List[ValidationIssue] = []
        
        for rule in rules:
            if not rule.validate(value, context.custom_context):
                issues.append(
                    ValidationIssue(
                        field=field_path,
                        message=rule.message,
                        severity=rule.severity
                    )
                )
        
        return issues
    
    def _get_value(
        self,
        data: Dict[str, Any],
        field_path: str
    ) -> Any:
        """
        Get value from data by path.
        
        Args:
            data: Data to get value from
            field_path: Path to field in dot notation
            
        Returns:
            Any: Field value
        """
        if not field_path:
            return data
        
        parts = field_path.split(".")
        value = data
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value 