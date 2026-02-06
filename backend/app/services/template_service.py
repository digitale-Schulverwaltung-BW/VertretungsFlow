"""
Template Service
Business logic for template variable processing and substitution
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for template variable processing"""

    def process_template_variable(self, template: str, context: Dict[str, Any]) -> str:
        """
        Process a single template variable with filters

        Args:
            template: Template string (e.g., "{{ absence.start_date | format_date('%d.%m.%Y') }}")
            context: Context dictionary

        Returns:
            Processed value as string
        """
        if not template or not isinstance(template, str):
            return ""

        # Remove {{ }} and whitespace
        template = template.strip()
        if template.startswith("{{") and template.endswith("}}"):
            template = template[2:-2].strip()
        else:
            # Not a template variable, return as-is
            return template

        # Check for filters (e.g., "absence.start_date | format_date('%d.%m.%Y')")
        if "|" in template:
            var_path, filter_expr = template.split("|", 1)
            var_path = var_path.strip()
            filter_expr = filter_expr.strip()

            # Extract value
            value = self.get_nested_value(context, var_path)

            # Apply filter
            return self.apply_filter(value, filter_expr)
        else:
            # No filter, just extract value
            value = self.get_nested_value(context, template)
            return str(value) if value is not None else ""

    def get_nested_value(self, context: Dict[str, Any], path: str) -> Any:
        """
        Get nested value from context using dot notation

        Args:
            context: Context dictionary
            path: Dot-separated path (e.g., "absence.teacher.full_name")

        Returns:
            Value or None if not found
        """
        keys = path.split(".")
        value = context

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.warning(f"Path not found in context: {path}")
                return None

        return value

    def apply_filter(self, value: Any, filter_expr: str) -> str:
        """
        Apply filter to value

        Args:
            value: Input value
            filter_expr: Filter expression (e.g., "format_date('%d.%m.%Y')")

        Returns:
            Filtered value as string
        """
        # Extract filter name and args
        match = re.match(r"(\w+)\((.*?)\)", filter_expr)
        if not match:
            logger.warning(f"Invalid filter expression: {filter_expr}")
            return str(value) if value is not None else ""

        filter_name = match.group(1)
        filter_args = match.group(2).strip("'\"")

        # Apply filter
        if filter_name == "format_date":
            if isinstance(value, datetime):
                return value.strftime(filter_args)
            else:
                logger.warning(f"format_date filter requires datetime, got {type(value)}")
                return str(value) if value is not None else ""
        else:
            logger.warning(f"Unknown filter: {filter_name}")
            return str(value) if value is not None else ""

    def process_field_mappings(
        self,
        field_mappings: Dict[str, str],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Process all field mappings with template variables

        Args:
            field_mappings: Dict of PDF field name -> template variable
            context: Context dictionary

        Returns:
            Dict of PDF field name -> filled value
        """
        filled_fields = {}

        for pdf_field_name, template in field_mappings.items():
            # Skip comment fields (start with _)
            if pdf_field_name.startswith("_"):
                continue

            # Process template variable
            value = self.process_template_variable(template, context)
            filled_fields[pdf_field_name] = value

        return filled_fields


# Singleton instance
template_service = TemplateService()
