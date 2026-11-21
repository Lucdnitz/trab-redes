"""Contratos compartilhados entre servidor, cliente e experimentos."""

from redes_audio.shared.protocol import AudioCodec, AudioPacket, PacketDecodeError

__all__ = ["AudioCodec", "AudioPacket", "PacketDecodeError"]
