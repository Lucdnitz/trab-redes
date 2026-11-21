"""Contrato binário dos datagramas de áudio.

O módulo usa apenas a biblioteca padrão para poder ser reutilizado no servidor, no cliente
desktop e nos experimentos headless.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum

MAGIC = b"RA"
PROTOCOL_VERSION = 1
HEADER = struct.Struct("!2sBBIQH")
MAX_PAYLOAD_SIZE = 1400 - HEADER.size


class AudioCodec(IntEnum):
    """Codecs identificados no cabeçalho."""

    PCM = 1
    OPUS = 2


class PacketDecodeError(ValueError):
    """Datagrama incompatível ou corrompido."""


@dataclass(frozen=True, slots=True)
class AudioPacket:
    """Um quadro de áudio com metadados estilo RTP."""

    sequence: int
    timestamp_samples: int
    payload: bytes
    codec: AudioCodec = AudioCodec.PCM
    version: int = PROTOCOL_VERSION

    def encode(self) -> bytes:
        """Serializa o pacote em ordem de rede."""
        if not 0 <= self.sequence <= 0xFFFFFFFF:
            raise ValueError("sequence must fit in uint32")
        if not 0 <= self.timestamp_samples <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError("timestamp_samples must fit in uint64")
        if len(self.payload) > MAX_PAYLOAD_SIZE:
            raise ValueError(f"payload exceeds {MAX_PAYLOAD_SIZE} bytes")

        header = HEADER.pack(
            MAGIC,
            self.version,
            int(self.codec),
            self.sequence,
            self.timestamp_samples,
            len(self.payload),
        )
        return header + self.payload

    @classmethod
    def decode(cls, datagram: bytes) -> AudioPacket:
        """Valida e desserializa um datagrama."""
        if len(datagram) < HEADER.size:
            raise PacketDecodeError("datagram is smaller than the protocol header")

        magic, version, codec_value, sequence, timestamp, payload_length = HEADER.unpack_from(
            datagram
        )
        if magic != MAGIC:
            raise PacketDecodeError("invalid packet magic")
        if version != PROTOCOL_VERSION:
            raise PacketDecodeError(f"unsupported protocol version: {version}")

        payload = datagram[HEADER.size :]
        if len(payload) != payload_length:
            raise PacketDecodeError("payload length does not match header")

        try:
            codec = AudioCodec(codec_value)
        except ValueError as exc:
            raise PacketDecodeError(f"unknown codec: {codec_value}") from exc

        return cls(
            sequence=sequence,
            timestamp_samples=timestamp,
            payload=payload,
            codec=codec,
            version=version,
        )
