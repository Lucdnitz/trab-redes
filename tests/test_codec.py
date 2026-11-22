import math
from array import array

import pytest

from redes_audio.shared.codec import FrameDecoder, FrameEncoder
from redes_audio.shared.protocol import AudioCodec


def _sine_pcm_frame(frame_index: int, samples_per_frame: int = 320) -> bytes:
    start = frame_index * samples_per_frame
    samples = array(
        "h",
        (
            int(8_000 * math.sin(2 * math.pi * 440 * (start + i) / 16_000))
            for i in range(samples_per_frame)
        ),
    )
    return samples.tobytes()


def test_pcm_codec_round_trip() -> None:
    encoder = FrameEncoder(AudioCodec.PCM, sample_rate=16_000, frame_ms=20)
    decoder = FrameDecoder(sample_rate=16_000, frame_ms=20)
    pcm = _sine_pcm_frame(0)

    encoded = encoder.encode(pcm)
    assert encoded == pcm
    assert decoder.decode(AudioCodec.PCM, encoded) == pcm


def test_opus_codec_compresses_and_decodes_to_fixed_frame_size() -> None:
    pytest.importorskip("av")
    encoder = FrameEncoder(AudioCodec.OPUS, sample_rate=16_000, frame_ms=20)
    decoder = FrameDecoder(sample_rate=16_000, frame_ms=20)

    encoded_sizes: list[int] = []
    for index in range(10):
        pcm = _sine_pcm_frame(index)
        encoded = encoder.encode(pcm)
        encoded_sizes.append(len(encoded))
        decoded = decoder.decode(AudioCodec.OPUS, encoded)
        assert len(decoded) == len(pcm) == 640

    assert max(encoded_sizes) < 200
    assert len(decoder.conceal_loss(AudioCodec.OPUS)) == 640
