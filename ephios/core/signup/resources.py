import dataclasses


@dataclasses.dataclass(frozen=True)
class Resource:
    id: int
    title: str
