"""Estado do resumo incremental da transmissão.

O módulo não chama um modelo diretamente. Ele mantém o contrato e prepara a entrada para
qualquer adaptador local, como Ollama, sem acoplar a sessão a um fornecedor específico.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import httpx

_STOPWORDS_PT = {
    "a", "as", "o", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "e", "ou", "que", "se", "por", "para", "com",
    "como", "mais", "mas", "ao", "aos", "à", "às", "já", "é", "são", "foi", "sobre",
    "entre", "até", "não", "sim", "isso", "este", "esta", "essa", "esse", "aqui",
}


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

    def __init__(
        self,
        *,
        minimum_pending_characters: int = 240,
        full_context_limit: int = 2_500,
    ) -> None:
        if minimum_pending_characters < 1:
            raise ValueError("minimum_pending_characters must be positive")
        self.minimum_pending_characters = minimum_pending_characters
        self.full_context_limit = full_context_limit
        self._pending: list[TranscriptSegment] = []
        self._history: list[str] = []
        self._snapshot = SummarySnapshot(text="", through_sequence=-1, through_ms=0)

    def reset(self) -> None:
        self._pending.clear()
        self._history.clear()
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

    def has_pending(self) -> bool:
        return bool(self._pending)

    def last_pending_sequence(self) -> int | None:
        return self._pending[-1].sequence if self._pending else None

    def pending_text(self) -> str:
        return " ".join(item.text.strip() for item in self._pending)

    def full_transcript_text(self) -> str:
        parts = [*self._history, self.pending_text()]
        return " ".join(part for part in parts if part).strip()

    def prompt(self) -> str:
        """Cria uma instrução curta para atualizar, não reescrever, o resumo."""
        if not self._pending:
            raise RuntimeError("there are no pending transcript segments")
        previous = self._snapshot.text or "(ainda não há resumo anterior)"
        return (
            "Você está criando um resumo ao vivo para um ouvinte que acabou de entrar no meio "
            "de uma apresentação. Escreva em português claro e em 3ª pessoa (por exemplo: "
            "'O palestrante explicou que...'), integrando o resumo anterior com os novos trechos "
            "em 2 a 4 frases coesas (máximo 90 palavras). Corrija pequenos erros fonéticos óbvios "
            "da transcrição sem inventar fatos novos. Responda SOMENTE com o resumo.\n\n"
            f"Resumo anterior: {previous}\n"
            f"Novos trechos falados: {self.pending_text()}\n\n"
            "Resumo:"
        )

    def confirm(self, text: str, *, up_to_sequence: int | None = None) -> SummarySnapshot:
        """Confirma a saída do modelo e avança até `up_to_sequence` (ou tudo)."""
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("summary text cannot be empty")
        if not self._pending:
            raise RuntimeError("there are no pending transcript segments")

        if up_to_sequence is None:
            committed = list(self._pending)
            remaining: list[TranscriptSegment] = []
        else:
            committed = [item for item in self._pending if item.sequence <= up_to_sequence]
            remaining = [item for item in self._pending if item.sequence > up_to_sequence]

        if not committed:
            raise RuntimeError("there are no pending transcript segments")

        self._history.extend(item.text.strip() for item in committed if item.text.strip())
        last = committed[-1]
        self._snapshot = SummarySnapshot(
            text=cleaned,
            through_sequence=last.sequence,
            through_ms=last.end_ms,
        )
        self._pending = remaining
        return self._snapshot

    def snapshot(self) -> SummarySnapshot:
        return self._snapshot


def summarize_extractive(
    previous_summary: str,
    new_text: str,
    *,
    max_words: int = 45,
    max_sentences: int = 2,
) -> str:
    """Resumo incremental extrativo que condensa os pontos principais em até 2 frases."""
    combined = " ".join(part for part in (previous_summary.strip(), new_text.strip()) if part)
    combined = combined.replace("...", " ").strip()
    raw_sentences = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+", combined) if len(s.strip().split()) >= 4
    ]
    if not raw_sentences:
        return " ".join(combined.split()[:max_words])

    unique_sentences: list[str] = []
    seen: set[str] = set()
    for sentence in raw_sentences:
        key = re.sub(r"\W+", " ", sentence.lower()).strip()
        if key and key not in seen:
            seen.add(key)
            unique_sentences.append(sentence)

    tokens_all = [
        tok
        for tok in re.findall(r"[a-zà-ú0-9]+", " ".join(unique_sentences).lower())
        if len(tok) > 2 and tok not in _STOPWORDS_PT
    ]
    freq = Counter(tokens_all)

    def score(idx: int, sentence: str) -> float:
        words = [
            tok
            for tok in re.findall(r"[a-zà-ú0-9]+", sentence.lower())
            if len(tok) > 2 and tok not in _STOPWORDS_PT
        ]
        if not words:
            return 0.0
        salience = sum(freq[w] for w in words) / len(words)
        recency_bonus = 0.25 * (idx / max(1, len(unique_sentences) - 1))
        return salience + recency_bonus

    ranked = sorted(
        enumerate(unique_sentences),
        key=lambda item: score(item[0], item[1]),
        reverse=True,
    )

    chosen_indices: list[int] = []
    word_budget = 0
    for idx, sentence in ranked:
        if len(chosen_indices) >= max_sentences:
            break
        words_in_sentence = len(sentence.split())
        if chosen_indices and word_budget + words_in_sentence > max_words:
            continue
        chosen_indices.append(idx)
        word_budget += words_in_sentence

    chosen_indices.sort()
    return " ".join(unique_sentences[idx] for idx in chosen_indices)


class SummaryEngine:
    """Atualiza o `RollingSummary` usando Ollama local ou fallback extrativo em CPU."""

    def __init__(
        self,
        rolling: RollingSummary,
        *,
        backend: str = "auto",
        ollama_url: str = "http://127.0.0.1:11434",
        ollama_model: str = "qwen2.5:1.5b",
    ) -> None:
        self.rolling = rolling
        self.backend = backend
        self.ollama_url = ollama_url.rstrip("/")
        self.ollama_model = ollama_model

    async def maybe_update(self, *, force: bool = False) -> tuple[SummarySnapshot, str] | None:
        if not self.rolling.has_pending():
            return None
        if not force and not self.rolling.ready():
            return None

        target_seq = self.rolling.last_pending_sequence()
        if target_seq is None:
            return None

        prompt = self.rolling.prompt()
        previous = self.rolling.snapshot().text
        new_text = self.rolling.pending_text()
        full_text = self.rolling.full_transcript_text()

        summary_text = ""
        used_backend = "extractive"
        if self.backend in {"auto", "ollama"}:
            summary_text = await self._try_ollama(previous, new_text, full_text, prompt)
            if summary_text:
                used_backend = f"ollama:{self.ollama_model}"
            elif self.backend == "ollama":
                summary_text = summarize_extractive(previous, new_text)
                used_backend = "extractive-fallback"

        if not summary_text:
            summary_text = summarize_extractive(previous, new_text)
            used_backend = "extractive"

        current_last = self.rolling.last_pending_sequence()
        if current_last is None:
            return None
        try:
            snapshot = self.rolling.confirm(summary_text, up_to_sequence=target_seq)
        except RuntimeError:
            return None
        return snapshot, used_backend

    async def _try_ollama(
        self,
        previous: str,
        new_text: str,
        full_text: str,
        _prompt: str,
    ) -> str:
        system_msg = (
            "Você resume apresentações em português para alguém que acabou de entrar na sala. "
            "Escreva em 3ª pessoa (ex.: 'O palestrante explicou que...') em 2 frases claras, "
            "corretas e completas (máximo 55 palavras). Nunca fale na 1ª pessoa ('eu consigo'), "
            "não copie frases inteiras do áudio e não invente nada que não esteja no texto."
        )
        if len(full_text) <= self.rolling.full_context_limit:
            user_msg = (
                f"Fala transcrita até o momento:\n\"{full_text}\"\n\n"
                "Escreva um resumo objetivo de tudo o que foi explicado até agora em 2 frases:"
            )
        else:
            prev_block = previous.strip() or "(ainda não há resumo anterior)"
            user_msg = (
                f"Resumo anterior: {prev_block}\n"
                f"Novas falas: {new_text}\n\n"
                "Atualize o resumo unindo as ideias antigas e as novas em 2 frases:"
            )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.ollama_model,
                        "stream": False,
                        "options": {
                            "temperature": 0.15,
                            "num_predict": 110,
                            "num_thread": 4,
                        },
                        "messages": [
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg},
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()
                raw = str(data.get("message", {}).get("content", "")).strip()
                return _clean_llm_summary(raw)
        except Exception:
            return ""


def _clean_llm_summary(text: str) -> str:
    cleaned = re.sub(
        r"^(resumo atualizado\s*:|aqui está[^\n:]*:)\s*",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    )
    return cleaned.strip()
