from enum import Enum, StrEnum


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Role(StrEnum):
    REQUESTER = "requester"
    TECHNICIAN = "technician"


RELACIONES = ("compañero", "docente", "encargado", "otro")
