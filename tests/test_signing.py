from redes_audio.shared.signing import TranscriptSigner, TranscriptVerifier


def test_ed25519_accepts_valid_caption_and_rejects_tampering() -> None:
    signer = TranscriptSigner.generate()
    verifier = TranscriptVerifier(signer.public_key_b64())

    sig = signer.sign(
        session_id="sess-1",
        sequence=0,
        start_ms=0,
        end_ms=4_000,
        text="O protocolo UDP prioriza baixa latência.",
    )

    assert verifier.verify(
        session_id="sess-1",
        sequence=0,
        start_ms=0,
        end_ms=4_000,
        text="O protocolo UDP prioriza baixa latência.",
        signature_b64=sig,
    )

    assert not verifier.verify(
        session_id="sess-1",
        sequence=0,
        start_ms=0,
        end_ms=4_000,
        text="O protocolo UDP garante entrega ordenada.",
        signature_b64=sig,
    )

    assert not verifier.verify(
        session_id="sess-1",
        sequence=0,
        start_ms=0,
        end_ms=4_000,
        text="O protocolo UDP prioriza baixa latência.",
        signature_b64="assinatura-invalida",
    )
