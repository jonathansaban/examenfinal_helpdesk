from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.domain.errors import TicketNotFoundError
from app.models.entities import ContactoAlterno, Ticket
from app.repositories.base import TicketRepository


class Base(DeclarativeBase):
    pass


@event.listens_for(Engine, "connect")
def _activar_claves_foraneas(dbapi_connection, _connection_record) -> None:
    """SQLite no aplica claves foráneas hasta que se piden. Solo afecta a esta conexión."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class TicketORM(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="open")
    requester_id: Mapped[int] = mapped_column()
    assignee_id: Mapped[int | None] = mapped_column(default=None)


def _to_domain(row: TicketORM) -> Ticket:
    """Traduce fila ORM -> dataclass de dominio (el servicio no conoce SQLAlchemy)."""
    return Ticket(
        id=row.id,
        title=row.title,
        description=row.description,
        category=row.category,
        priority=row.priority,
        requester_id=row.requester_id,
        status=row.status,
        assignee_id=row.assignee_id,
    )


class SqlAlchemyTicketRepository(TicketRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, ticket: Ticket) -> Ticket:
        self._session.add(
            TicketORM(
                id=ticket.id,
                title=ticket.title,
                description=ticket.description,
                category=ticket.category,
                priority=ticket.priority,
                status=ticket.status,
                requester_id=ticket.requester_id,
                assignee_id=ticket.assignee_id,
            )
        )
        self._session.flush()
        return ticket

    def by_id(self, ticket_id: int) -> Ticket | None:
        row = self._session.get(TicketORM, ticket_id)
        return None if row is None else _to_domain(row)

    def list(self, *, status=None, assignee_id=None, requester_id=None) -> list[Ticket]:
        stmt = select(TicketORM).order_by(TicketORM.id)
        if status is not None:
            stmt = stmt.where(TicketORM.status == getattr(status, "value", status))
        if assignee_id is not None:
            stmt = stmt.where(TicketORM.assignee_id == assignee_id)
        if requester_id is not None:
            stmt = stmt.where(TicketORM.requester_id == requester_id)
        return [_to_domain(row) for row in self._session.scalars(stmt)]

    def next_id(self) -> int:
        current = self._session.scalar(select(func.coalesce(func.max(TicketORM.id), 0)))
        return current + 1

    def update(self, ticket: Ticket) -> None:
        row = self._session.get(TicketORM, ticket.id)
        if row is None:
            raise TicketNotFoundError(f"Ticket {ticket.id} no encontrado")
        row.title = ticket.title
        row.description = ticket.description
        row.category = ticket.category
        row.priority = ticket.priority
        row.status = getattr(ticket.status, "value", ticket.status)
        row.requester_id = ticket.requester_id
        row.assignee_id = ticket.assignee_id
        self._session.flush()

    def count_by_status(self) -> dict[str, int]:
        """Reporte agregado: solo los estados presentes; {} si no hay tickets."""
        stmt = select(TicketORM.status, func.count()).group_by(TicketORM.status)
        return {status: total for status, total in self._session.execute(stmt).all()}


class AlternateContactORM(Base):
    __tablename__ = "alternate_contacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20))
    relationship: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(200))
    added_by: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _contact_to_domain(row: AlternateContactORM) -> ContactoAlterno:
    return ContactoAlterno(
        id=row.id,
        ticket_id=row.ticket_id,
        name=row.name,
        phone=row.phone,
        relationship=row.relationship,
        reason=row.reason,
        added_by=row.added_by,
        created_at=row.created_at,
    )


class SqlAlchemyAlternateContactRepository:
    """Alta y consulta de contactos alternos. El id lo asigna la base."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, contact: ContactoAlterno) -> ContactoAlterno:
        row = AlternateContactORM(
            ticket_id=contact.ticket_id,
            name=contact.name,
            phone=contact.phone,
            relationship=contact.relationship,
            reason=contact.reason,
            added_by=contact.added_by,
            created_at=contact.created_at,
        )
        self._session.add(row)
        self._session.flush()
        contact.id = row.id
        return contact

    def list_by_ticket(self, ticket_id: int) -> list[ContactoAlterno]:
        stmt = (
            select(AlternateContactORM)
            .where(AlternateContactORM.ticket_id == ticket_id)
            .order_by(AlternateContactORM.id)
        )
        return [_contact_to_domain(row) for row in self._session.scalars(stmt)]
