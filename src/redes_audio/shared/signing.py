"""Assinatura digital Ed25519 para integridade das legendas enviadas via WebSocket."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)


def canonical_transcript_bytes(
    *,
    session_id: str,
    sequence: int,
    start_ms: int,
    end_ms: int,
    text: str,
) -> bytes:
    """Serializa os campos protegidos da legenda de forma determinística."""
    payload: dict[str, Any] = {
        "session_id": session_id,
        "sequence": int(sequence),
        "start_ms": int(start_ms),
        "end_ms": int(end_ms),
        "text": text,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


@dataclass(slots=True)
class TranscriptSigner:
    """Assina trechos transcritos no servidor usando Ed25519."""

    _private_key: Ed25519PrivateKey

    @classmethod
    def generate(cls) -> TranscriptSigner:
        return cls(_private_key=Ed25519PrivateKey.generate())

    def public_key_b64(self) -> str:
        raw = self._private_key.public_key().public_bytes(
            encoding=Encoding.Raw,
            format=PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("ascii")

    def sign(
        self,
        *,
        session_id: str,
        sequence: int,
        start_ms: int,
        end_ms: int,
        text: str,
    ) -> str:
        message = canonical_transcript_bytes(
            session_id=session_id,
            sequence=sequence,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
        )
        signature = self._private_key.sign(message)
        return base64.b64encode(signature).decode("ascii")


class TranscriptVerifier:
    """Verifica a assinatura Ed25519 das legendas recebidas pelo cliente."""

    def __init__(self, public_key_b64: str) -> None:
        raw = base64.b64decode(public_key_b64.encode("ascii"), validate=True)
        self._public_key = Ed25519PublicKey.from_public_bytes(raw)

    def verify(
        self,
        *,
        session_id: str,
        sequence: int,
        start_ms: int,
        end_ms: int,
        text: str,
        signature_b64: str,
    ) -> bool:
        if not signature_b64:
            return False
        try:
            signature = base64.b64decode(signature_b64.encode("ascii"), validate=True)
        except ValueError:
            return False

        message = canonical_transcript_bytes(
            session_id=session_id,
            sequence=sequence,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
        )
        try:
            self._public_key.verify(signature, message)
        except InvalidSignature:
            return False
        return True
