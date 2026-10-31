import enum
from typing import Any, Optional, Type, TypeVar
from fastapi import HTTPException, status

E = TypeVar("E", bound=enum.Enum)


class EnumValidationError(HTTPException, ValueError):
    """Exception that inherits from both HTTPException and ValueError so that:
    1. Direct raise in route returns HTTP 422 with clear message listing allowed values.
    2. Raise inside Pydantic field_validator raises ValueError (which Pydantic converts to 422
       and pytest catches with ValidationError).
    """

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    def __str__(self) -> str:
        return self.detail


def normalize_key(s: str) -> str:
    """Normalize string for robust case-insensitive and symbol-agnostic enum lookup."""
    return s.strip().lower().replace("-", "").replace("_", "").replace(" ", "")


def coerce_enum(
    enum_cls: Type[E],
    val: Any,
    field_name: Optional[str] = None,
    allow_none: bool = True,
) -> Optional[E]:
    """
    Converts a value to an Enum instance case-insensitively and returns it.
    
    If val is None:
      - returns None if allow_none is True
      - raises EnumValidationError (422) if allow_none is False
      
    If val matches an enum value or name (case-insensitively, ignoring hyphens/underscores/spaces):
      - returns the Enum member
      
    If val is invalid:
      - raises EnumValidationError (HTTP 422) listing the allowed values.
    """
    name = field_name or enum_cls.__name__
    allowed = [e.value for e in enum_cls]

    if val is None:
        if allow_none:
            return None
        raise EnumValidationError(
            f"Invalid {name}: None. Allowed values: {allowed}"
        )

    if isinstance(val, enum_cls):
        return val

    if hasattr(val, "value") and isinstance(val.value, (str, int)):
        val = val.value

    val_str = str(val).strip()
    norm_val = normalize_key(val_str)

    # 1. Exact value match
    for member in enum_cls:
        if member.value == val:
            return member

    # 2. Normalized value match (case-insensitive, no -, _, or space)
    for member in enum_cls:
        if normalize_key(str(member.value)) == norm_val:
            return member

    # 3. Normalized member name match
    for member in enum_cls:
        if normalize_key(member.name) == norm_val:
            return member

    raise EnumValidationError(
        f"Invalid {name}: '{val}'. Allowed values: {allowed}"
    )
