from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from app.domain.errors import NotFoundError, UserNotFoundError, ValidationError
from app.models.entities import User
from app.repositories.sqlalchemy import (
    SqlAlchemyAlternateContactRepository,
    SqlAlchemyTicketRepository,
)
from app.services.contacts import AlternateContactService
from app.services.users import UserService

_PAGE = Path(__file__).resolve().parent / "web" / "ticket.html"


class ContactIn(BaseModel):
    name: str
    phone: str
    relationship: str
    reason: str


class ContactOut(BaseModel):
    id: int
    ticket_id: int
    name: str
    phone: str
    relationship: str
    reason: str
    added_by: int
    created_at: datetime


def create_app(session_factory: sessionmaker[Session], users: UserService) -> FastAPI:
    app = FastAPI(title="HelpDesk EDU")

    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def current_user(x_user_id: str | None = Header(default=None)) -> User:
        if x_user_id is None or not x_user_id.isdigit():
            raise HTTPException(status_code=401, detail="Actor no autenticado")
        try:
            return users.require(int(x_user_id))
        except UserNotFoundError:
            raise HTTPException(status_code=401, detail="Actor no autenticado")

    def finish(session: Session, action):
        try:
            result = action()
            session.commit()
            return result
        except ValidationError as error:
            session.rollback()
            raise HTTPException(status_code=422, detail=str(error))
        except NotFoundError as error:
            session.rollback()
            raise HTTPException(status_code=404, detail=str(error))

    @app.get("/tickets/{ticket_id}")
    def ticket_page(ticket_id: int):
        return FileResponse(_PAGE)

    @app.get("/api/tickets/{ticket_id}")
    def get_ticket(
        ticket_id: int,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ):
        contacts = AlternateContactService(
            SqlAlchemyTicketRepository(session),
            SqlAlchemyAlternateContactRepository(session),
        )

        def read():
            ticket = contacts.visible_ticket(actor, ticket_id)
            return {
                "id": ticket.id,
                "title": ticket.title,
                "status": getattr(ticket.status, "value", ticket.status),
            }

        return finish(session, read)

    @app.get("/api/tickets/{ticket_id}/alternate-contacts", response_model=list[ContactOut])
    def list_contacts(
        ticket_id: int,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ):
        contacts = AlternateContactService(
            SqlAlchemyTicketRepository(session),
            SqlAlchemyAlternateContactRepository(session),
        )
        return finish(session, lambda: contacts.list(actor, ticket_id))

    @app.post(
        "/api/tickets/{ticket_id}/alternate-contacts",
        response_model=ContactOut,
        status_code=201,
    )
    def add_contact(
        ticket_id: int,
        body: ContactIn,
        actor: User = Depends(current_user),
        session: Session = Depends(get_session),
    ):
        contacts = AlternateContactService(
            SqlAlchemyTicketRepository(session),
            SqlAlchemyAlternateContactRepository(session),
        )
        return finish(
            session,
            lambda: contacts.add(
                actor,
                ticket_id,
                body.name,
                body.phone,
                body.relationship,
                body.reason,
            ),
        )

    return app
