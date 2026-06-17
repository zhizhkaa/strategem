"""Built-in player document slots exposed through the documents API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerDocumentSlot:
    slot: str
    title: str
    scope: str
    minister: str | None
    filename: str
    order: int

    @property
    def static_path(self) -> str:
        return f"docs/players/{self.filename}"


PLAYER_DOCUMENT_SLOTS = [
    PlayerDocumentSlot(
        slot="glossary",
        title="Словарь терминов",
        scope="general",
        minister=None,
        filename="glossary.pdf",
        order=10,
    ),
    PlayerDocumentSlot(
        slot="common_mistakes",
        title="Основные ошибки",
        scope="general",
        minister=None,
        filename="common-mistakes.pdf",
        order=20,
    ),
    PlayerDocumentSlot(
        slot="minister_population",
        title="Министр по проблемам населения",
        scope="minister",
        minister="population",
        filename="minister-population.pdf",
        order=110,
    ),
    PlayerDocumentSlot(
        slot="minister_energy",
        title="Министр энергетики",
        scope="minister",
        minister="energy",
        filename="minister-energy.pdf",
        order=120,
    ),
    PlayerDocumentSlot(
        slot="minister_industry",
        title="Министр промышленности и социальных услуг",
        scope="minister",
        minister="industry",
        filename="minister-industry.pdf",
        order=130,
    ),
    PlayerDocumentSlot(
        slot="minister_agriculture",
        title="Министр сельского хозяйства и охраны окружающей среды",
        scope="minister",
        minister="agriculture",
        filename="minister-agriculture.pdf",
        order=140,
    ),
    PlayerDocumentSlot(
        slot="minister_trade_finance",
        title="Министр внешней торговли и финансов",
        scope="minister",
        minister="trade_finance",
        filename="minister-trade-finance.pdf",
        order=150,
    ),
]

PLAYER_DOCUMENT_SLOT_BY_ID = {slot.slot: slot for slot in PLAYER_DOCUMENT_SLOTS}
