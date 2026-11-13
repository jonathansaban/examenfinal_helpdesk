from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.errors import ValidationError
from app.models.enums import Role


@dataclass
class HistoryEvent:
    action: str
    detail: str
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass
class Ticket:
    id: int
    title: str
    description: str
    category: str
    priority: str
    requester_id: int
    status: str = "open"
    assignee_id: Optional[int] = None
    history: list[HistoryEvent] = field(default_factory=list)
    _tags: list[str] = field(default_factory=list, init=False, repr=False)

    @property
    def tags(self) -> tuple[str, ...]:
        """Solo lectura: devuelve una tupla, no la lista interna."""
        return tuple(self._tags)

    def add_tag(self, tag: str) -> None:
        """Agrega una etiqueta normalizada (strip + lower), sin vacias ni duplicados."""
        clean = tag.strip().lower()
        if not clean:
            raise ValidationError("La etiqueta no puede estar vacia")
        if clean not in self._tags:
            self._tags.append(clean)


@dataclass
class User:
    id: int
    name: str
    role: Role


@dataclass
class ContactoAlterno:
    """Persona de contacto del caso. No es un User del sistema."""

    ticket_id: int
    name: str
    phone: str
    relationship: str
    reason: str
    added_by: int
    id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
