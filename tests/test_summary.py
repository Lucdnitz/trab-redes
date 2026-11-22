import pytest

from redes_audio.server.summary import RollingSummary, SummaryEngine, TranscriptSegment


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


@pytest.mark.asyncio
async def test_summary_engine_updates_incrementally_with_extractive_backend() -> None:
    rolling = RollingSummary(minimum_pending_characters=20)
    engine = SummaryEngine(rolling, backend="extractive")

    rolling.add(segment(0, "O protocolo UDP envia pacotes de áudio sem esperar retransmissão."))
    rolling.add(segment(1, "O jitter buffer absorve variações de atraso no cliente."))

    result = await engine.maybe_update()
    assert result is not None
    snapshot, backend = result
    assert backend == "extractive"
    assert snapshot.through_sequence == 1
    assert "UDP" in snapshot.text or "jitter" in snapshot.text


def test_confirm_up_to_sequence_preserves_newer_pending_segments() -> None:
    summary = RollingSummary(minimum_pending_characters=10)
    summary.add(segment(0, "Primeiro trecho da palestra."))
    summary.add(segment(1, "Segundo trecho chegou depois."))

    snapshot = summary.confirm("Resumo inicial.", up_to_sequence=0)
    assert snapshot.through_sequence == 0
    assert snapshot.through_ms == 1_000
    assert summary.pending_text() == "Segundo trecho chegou depois."
