import re

from app.domain.errors import TicketNotFoundError, ValidationError
from app.models.entities import ContactoAlterno, User
from app.models.enums import RELACIONES, Role
from app.repositories.base import TicketRepository
from app.repositories.sqlalchemy import SqlAlchemyAlternateContactRepository

_PHONE = re.compile(r"^[0-9 +\-]+$")


class AlternateContactService:
    """Regla de la ficha: quién puede agregar un contacto y cuándo se rechaza."""

    def __init__(
        self,
        tickets: TicketRepository,
        contacts: SqlAlchemyAlternateContactRepository,
    ) -> None:
        self._tickets = tickets
        self._contacts = contacts

    def add(
        self,
        actor: User,
        ticket_id: int,
        name: str,
        phone: str,
        relationship: str,
        reason: str,
    ) -> ContactoAlterno:
        ticket = self._visible_ticket(actor, ticket_id)
        status = getattr(ticket.status, "value", ticket.status)
        if status == "closed":
            raise ValidationError("El ticket no esta abierto")

        clean_name = name.strip()
        clean_reason = reason.strip()
        clean_phone = phone.strip()
        if not clean_name:
            raise ValidationError("El nombre es obligatorio")
        if not clean_reason:
            raise ValidationError("El motivo es obligatorio")
        if relationship not in RELACIONES:
            raise ValidationError("La relacion no esta permitida")
        if _PHONE.fullmatch(clean_phone) is None:
            raise ValidationError("El telefono solo admite digitos, espacios, guiones y +")
        digits = re.sub(r"\D", "", clean_phone)
        if not 8 <= len(digits) <= 15:
            raise ValidationError("El telefono debe tener entre 8 y 15 digitos")

        contact = ContactoAlterno(
            ticket_id=ticket_id,
            name=clean_name,
            phone=clean_phone,
            relationship=relationship,
            reason=clean_reason,
            added_by=actor.id,
        )
        return self._contacts.add(contact)

    def list(self, actor: User, ticket_id: int) -> list[ContactoAlterno]:
        self._visible_ticket(actor, ticket_id)
        return self._contacts.list_by_ticket(ticket_id)

    def visible_ticket(self, actor: User, ticket_id: int):
        return self._visible_ticket(actor, ticket_id)

    def _visible_ticket(self, actor: User, ticket_id: int):
        ticket = self._tickets.by_id(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} no encontrado")
        # Quien no participa no se entera de que el ticket existe.
        if actor.role != Role.TECHNICIAN and actor.id != ticket.requester_id:
            raise TicketNotFoundError(f"Ticket {ticket_id} no encontrado")
        return ticket
