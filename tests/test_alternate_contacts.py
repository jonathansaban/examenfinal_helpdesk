from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import create_app
from app.models.entities import Ticket
from app.models.enums import Role
from app.repositories.sqlalchemy import Base, SqlAlchemyAlternateContactRepository, SqlAlchemyTicketRepository
from app.services.users import UserService

VALID = {
    "name": "Mateo",
    "phone": "5551-2040",
    "relationship": "compañero",
    "reason": "tiene la llave del laboratorio",
}


def build():
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    users = UserService()
    ana = users.register("Ana", Role.REQUESTER)
    users.register("Bruno", Role.REQUESTER)
    users.register("Luis", Role.TECHNICIAN)

    session = Session()
    SqlAlchemyTicketRepository(session).add(
        Ticket(
            id=1,
            title="La impresora del laboratorio 2 no imprime",
            description="Ana estara en clase",
            category="Hardware",
            priority="High",
            requester_id=ana.id,
            status="open",
        )
    )
    session.commit()
    session.close()
    return TestClient(create_app(Session, users)), Session


def test_telefono_corto_se_rechaza_sin_cambiar_la_lista():
    client, Session = build()

    rejected = client.post(
        "/api/tickets/1/alternate-contacts",
        headers={"X-User-Id": "1"},
        json={**VALID, "phone": "555"},
    )
    assert rejected.status_code == 422

    session = Session()
    saved = SqlAlchemyAlternateContactRepository(session).list_by_ticket(1)
    session.close()
    assert saved == []

    listed = client.get("/api/tickets/1/alternate-contacts", headers={"X-User-Id": "1"})
    assert listed.status_code == 200
    assert listed.json() == []


def test_contacto_valido_sigue_en_otra_sesion():
    client, Session = build()

    created = client.post(
        "/api/tickets/1/alternate-contacts",
        headers={"X-User-Id": "1"},
        json=VALID,
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Mateo"
    assert created.json()["phone"] == "5551-2040"

    session = Session()
    saved = SqlAlchemyAlternateContactRepository(session).list_by_ticket(1)
    session.close()
    assert len(saved) == 1
    assert saved[0].reason == "tiene la llave del laboratorio"
    assert saved[0].added_by == 1


def test_otro_solicitante_recibe_404_y_no_crea_contacto():
    client, Session = build()

    hidden = client.post(
        "/api/tickets/1/alternate-contacts",
        headers={"X-User-Id": "2"},
        json=VALID,
    )
    assert hidden.status_code == 404

    session = Session()
    saved = SqlAlchemyAlternateContactRepository(session).list_by_ticket(1)
    session.close()
    assert saved == []


def test_la_pantalla_ofrece_el_formulario():
    client, _Session = build()
    page = client.get("/tickets/1")
    assert page.status_code == 200
    assert "Contactos alternos" in page.text
    assert "Agregar" in page.text
