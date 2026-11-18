"""Optional live microphone transcription using Faster-Whisper."""

from __future__ import annotations

import queue
import threading

import numpy as np
import sounddevice as sd

from app.providers.stage1_speech_to_text_faster_whisper import (
    FasterWhisperSTTProvider,
    configure_cuda_dll_paths,
)


SAMPLERATE = 16_000
BLOCK_DURATION_SECONDS = 0.5
CHUNK_DURATION_SECONDS = 3.0
CHANNELS = 1


def main() -> None:
    configure_cuda_dll_paths()

    provider = FasterWhisperSTTProvider(
        model_id="large-v3-turbo",
        device="cuda",
        compute_type="float16",
    )
    model = provider.load_model()

    frames_per_block = int(SAMPLERATE * BLOCK_DURATION_SECONDS)
    frames_per_chunk = int(SAMPLERATE * CHUNK_DURATION_SECONDS)
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()
    audio_buffer: list[np.ndarray] = []

    def audio_callback(
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        del frames, time_info
        if status:
            print(status)
        audio_queue.put(indata.copy())

    def recorder() -> None:
        with sd.InputStream(
            samplerate=SAMPLERATE,
            channels=CHANNELS,
            callback=audio_callback,
            blocksize=frames_per_block,
        ):
            print("Listening... Press Ctrl+C to stop.")
            while True:
                sd.sleep(100)

    def transcriber() -> None:
        while True:
            block = audio_queue.get()
            audio_buffer.append(block)
            total_frames = sum(len(current) for current in audio_buffer)

            if total_frames >= frames_per_chunk:
                audio_data = np.concatenate(audio_buffer, axis=0)[:frames_per_chunk]
                audio_buffer.clear()
                audio_data = audio_data.flatten().astype(np.float32)

                segments, _ = model.transcribe(
                    audio_data,
                    language=None,
                    beam_size=3,
                    temperature=0.0,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                for segment in segments:
                    text = str(segment.text).strip()
                    if text:
                        print(text)

    threading.Thread(target=recorder, daemon=True).start()
    try:
        transcriber()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
