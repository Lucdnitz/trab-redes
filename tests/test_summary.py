import pytest

from redes_audio.server.summary import RollingSummary, TranscriptSegment


def segment(sequence: int, text: str) -> TranscriptSegment:
    return TranscriptSegment(
        sequence=sequence,
        start_ms=sequence * 1_000,
        end_ms=(sequence + 1) * 1_000,
        text=text,
    )


def test_builds_incremental_prompt_and_confirms_snapshot() -> None:
    summary = RollingSummary(minimum_pending_characters=10)
    assert summary.add(segment(0, "A aula apresentou o protocolo UDP."))
    assert summary.ready()
    assert "protocolo UDP" in summary.prompt()

    snapshot = summary.confirm("A aula introduziu o protocolo UDP.")
    assert snapshot.through_sequence == 0
    assert snapshot.through_ms == 1_000
    assert summary.pending_text() == ""


def test_rejects_duplicate_or_regressive_segment() -> None:
    summary = RollingSummary(minimum_pending_characters=1)
    assert summary.add(segment(2, "Primeiro trecho recebido."))
    assert summary.add(segment(2, "Trecho repetido.")) is False
    assert summary.add(segment(1, "Trecho atrasado.")) is False


def test_requires_pending_segments_before_confirmation() -> None:
    summary = RollingSummary()

    with pytest.raises(RuntimeError, match="no pending"):
        summary.confirm("Resumo")
