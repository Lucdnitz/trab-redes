"""Estado do resumo incremental da transmissão.

O módulo não chama um modelo diretamente. Ele mantém o contrato e prepara a entrada para
qualquer adaptador local, como Ollama, sem acoplar a sessão a um fornecedor específico.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    sequence: int
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True, slots=True)
class SummarySnapshot:
    text: str
    through_sequence: int
    through_ms: int


class RollingSummary:
    """Acumula somente segmentos ainda não incorporados ao resumo confirmado."""

    def __init__(self, *, minimum_pending_characters: int = 240) -> None:
        if minimum_pending_characters < 1:
            raise ValueError("minimum_pending_characters must be positive")
        self.minimum_pending_characters = minimum_pending_characters
        self._pending: list[TranscriptSegment] = []
        self._snapshot = SummarySnapshot(text="", through_sequence=-1, through_ms=0)

    def add(self, segment: TranscriptSegment) -> bool:
        """Adiciona um segmento novo; duplicados ou regressões são rejeitados."""
        last_sequence = (
            self._pending[-1].sequence if self._pending else self._snapshot.through_sequence
        )
        if segment.sequence <= last_sequence:
            return False
        if segment.end_ms < segment.start_ms:
            raise ValueError("segment end_ms must be greater than or equal to start_ms")
        if not segment.text.strip():
            return False
        self._pending.append(segment)
        return True

    def ready(self) -> bool:
        return len(self.pending_text()) >= self.minimum_pending_characters

    def pending_text(self) -> str:
        return " ".join(item.text.strip() for item in self._pending)

    def prompt(self) -> str:
        """Cria uma instrução curta para atualizar, não reescrever, o resumo."""
        if not self._pending:
            raise RuntimeError("there are no pending transcript segments")
        previous = self._snapshot.text or "(nenhum resumo anterior)"
        return (
            "Atualize o resumo da transmissão em português. Preserve fatos importantes, "
            "não invente informações e use no máximo 120 palavras.\n\n"
            f"Resumo anterior:\n{previous}\n\n"
            f"Novos trechos:\n{self.pending_text()}"
        )

    def confirm(self, text: str) -> SummarySnapshot:
        """Confirma a saída do modelo e avança o ponto processado."""
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("summary text cannot be empty")
        if not self._pending:
            raise RuntimeError("there are no pending transcript segments")

        last = self._pending[-1]
        self._snapshot = SummarySnapshot(
            text=cleaned,
            through_sequence=last.sequence,
            through_ms=last.end_ms,
        )
        self._pending.clear()
        return self._snapshot

    def snapshot(self) -> SummarySnapshot:
        return self._snapshot
