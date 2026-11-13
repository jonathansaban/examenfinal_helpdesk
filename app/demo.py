"""Arranque local con una base SQLite aislada. No usa la base del curso."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import create_app
from app.models.entities import Ticket
from app.models.enums import Role
from app.repositories.sqlalchemy import Base, SqlAlchemyTicketRepository
from app.services.users import UserService

_DB = Path(__file__).resolve().parents[1] / "pruebas_helpdesk.sqlite"
_engine = create_engine(f"sqlite:///{_DB}")
Base.metadata.create_all(_engine)
SessionLocal = sessionmaker(bind=_engine)

users = UserService()
users.register("Ana", Role.REQUESTER)
users.register("Bruno", Role.REQUESTER)
users.register("Luis", Role.TECHNICIAN)

_session = SessionLocal()
try:
    tickets = SqlAlchemyTicketRepository(_session)
    if tickets.by_id(1) is None:
        tickets.add(
            Ticket(
                id=1,
                title="La impresora del laboratorio 2 no imprime",
                description="Ana estara en clase",
                category="Hardware",
                priority="High",
                requester_id=1,
                status="open",
                assignee_id=3,
            )
        )
        _session.commit()
finally:
    _session.close()

app = create_app(SessionLocal, users)
