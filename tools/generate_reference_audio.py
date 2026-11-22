"""Gera áudios de referência em português (16 kHz, mono, int16) e seus gabaritos.

Executa no Windows usando SAPI (`Microsoft Maria Desktop`) e PyAV para reamostragem
exata para 16 kHz mono int16. Os arquivos gerados em `data/reference/` funcionam em
qualquer sistema (Windows, Linux ou WSL2) sem depender de TTS na apresentação.
"""

from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import av
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF_DIR = ROOT / "data" / "reference"

DEMO_TEXT = (
    "Bem-vindos à aula de Redes de Computadores sobre transmissão de áudio ao vivo. "
    "Quando enviamos voz em tempo real, usamos o protocolo U D P porque ele prioriza "
    "baixa latência e não trava o som esperando retransmissões. "
    "Já as legendas e o resumo usam WebSocket sobre T C P, pois o texto precisa chegar "
    "completo e na ordem correta. "
    "No cliente, o jitter buffer guarda cem milissegundos de áudio para absorver "
    "variações de atraso da rede e reordenar pacotes que chegam fora de sequência. "
    "Por fim, o formato Opus reduz muito o consumo de banda em comparação ao áudio "
    "cru em P C M, mantendo a fala compreensível para o ouvinte."
)

EXPERIMENT_TEXT = (
    "Na aula de Redes estudamos a diferença entre os protocolos U D P e T C P. "
    "O áudio ao vivo tolera pequenas perdas, mas exige atraso baixo para não travar. "
    "O jitter buffer do cliente organiza os pacotes antes da reprodução final. "
    "Com o codec Opus enviamos menos bytes por segundo pela rede sem perder clareza."
)


def _synthesize_to_16k_wav(text: str, target_wav: Path) -> float:
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_wav = Path(tmp_dir) / "raw.wav"
        ps_script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.SelectVoice('Microsoft Maria Desktop'); "
            "$s.Rate = 0; "
            f"$s.SetOutputToWaveFile('{raw_wav}'); "
            f"$s.Speak('{text.replace(chr(39), chr(39) * 2)}'); "
            "$s.Dispose()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            check=True,
        )

        resampler = av.AudioResampler(format="s16", layout="mono", rate=16_000)
        pcm_chunks: list[bytes] = []
        with av.open(str(raw_wav)) as container:
            for frame in container.decode(audio=0):
                for out_frame in resampler.resample(frame):
                    pcm_chunks.append(out_frame.to_ndarray().astype(np.int16, copy=False).tobytes())
            for out_frame in resampler.resample(None):
                pcm_chunks.append(out_frame.to_ndarray().astype(np.int16, copy=False).tobytes())

        pcm = b"".join(pcm_chunks)
        target_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(target_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16_000)
            wf.writeframes(pcm)

        return len(pcm) / (16_000 * 2)


def main() -> None:
    REF_DIR.mkdir(parents=True, exist_ok=True)
    demo_wav = REF_DIR / "aula_redes.wav"
    exp_wav = REF_DIR / "aula_redes_exp.wav"

    demo_dur = _synthesize_to_16k_wav(DEMO_TEXT, demo_wav)
    (REF_DIR / "aula_redes.txt").write_text(DEMO_TEXT + "\n", encoding="utf-8")

    exp_dur = _synthesize_to_16k_wav(EXPERIMENT_TEXT, exp_wav)
    (REF_DIR / "aula_redes_exp.txt").write_text(EXPERIMENT_TEXT + "\n", encoding="utf-8")

    print(f"Demo WAV: {demo_wav} ({demo_dur:.2f}s)")
    print(f"Exp WAV:  {exp_wav} ({exp_dur:.2f}s)")


if __name__ == "__main__":
    main()
