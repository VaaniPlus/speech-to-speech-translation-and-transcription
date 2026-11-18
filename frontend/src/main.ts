type UIElements = {
  direction: HTMLSelectElement;
  "source-language": HTMLSpanElement;
  "target-language": HTMLSpanElement;
  "source-pill": HTMLSpanElement;
  "target-pill": HTMLSpanElement;
  "text-mode-button": HTMLButtonElement;
  "voice-mode-button": HTMLButtonElement;
  "text-input-mode": HTMLElement;
  "voice-input-mode": HTMLElement;
  "source-text": HTMLTextAreaElement;
  "demo-text-select": HTMLSelectElement;
  "character-count": HTMLSpanElement;
  "translate-button": HTMLButtonElement;
  "translate-button-label": HTMLSpanElement;
  "result-placeholder-content": HTMLElement;
  "translation-output": HTMLElement;
  "source-output": HTMLParagraphElement;
  "translated-output": HTMLParagraphElement;
  "workspace-status": HTMLElement;
  "workspace-status-text": HTMLSpanElement;
  "workspace-status-icon": HTMLSpanElement;
  "record-button": HTMLButtonElement;
  "stop-button": HTMLButtonElement;
  "recording-status": HTMLSpanElement;
  "recording-indicator": HTMLElement;
  "speech-submit-button": HTMLButtonElement;
  "speech-submit-label": HTMLSpanElement;
  "audio-status": HTMLSpanElement;
  "audio-toggle-button": HTMLButtonElement;
  "audio-toggle-label": HTMLSpanElement;
  "audio-replay-button": HTMLButtonElement;
  "translated-audio": HTMLAudioElement;
  "reset-button": HTMLButtonElement;
};

function getElement<K extends keyof UIElements>(id: K): UIElements[K] {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing required UI element: #${id}`);
  return element as UIElements[K];
}

const directionSelect = getElement("direction");
const sourceLanguage = getElement("source-language");
const targetLanguage = getElement("target-language");
const sourcePill = getElement("source-pill");
const targetPill = getElement("target-pill");
const textModeButton = getElement("text-mode-button");
const voiceModeButton = getElement("voice-mode-button");
const textInputMode = getElement("text-input-mode");
const voiceInputMode = getElement("voice-input-mode");
const sourceText = getElement("source-text");
const demoTextSelect = getElement("demo-text-select");
const characterCount = getElement("character-count");
const translateButton = getElement("translate-button");
const translateButtonLabel = getElement("translate-button-label");
const placeholderContent = getElement("result-placeholder-content");
const translationOutput = getElement("translation-output");
const sourceOutput = getElement("source-output");
const translatedOutput = getElement("translated-output");
const workspaceStatus = getElement("workspace-status");
const workspaceStatusText = getElement("workspace-status-text");
const workspaceStatusIcon = getElement("workspace-status-icon");
const recordButton = getElement("record-button");
const stopButton = getElement("stop-button");
const recordingStatus = getElement("recording-status");
const recordingIndicator = getElement("recording-indicator");
const speechSubmitButton = getElement("speech-submit-button");
const speechSubmitLabel = getElement("speech-submit-label");
const audioStatus = getElement("audio-status");
const audioToggleButton = getElement("audio-toggle-button");
const audioToggleLabel = getElement("audio-toggle-label");
const audioReplayButton = getElement("audio-replay-button");
const translatedAudio = getElement("translated-audio");
const resetButton = getElement("reset-button");

const directions: Record<string, {
  source: string;
  target: string;
  targetCode: string;
  sourcePill: string;
  targetPill: string;
  placeholder: string;
  demoTexts: { label: string; text: string }[];
}> = {
  "en-to-hi": {
    source: "English",
    target: "हिन्दी",
    targetCode: "hi",
    sourcePill: "ENGLISH",
    targetPill: "हिन्दी · HINDI",
    placeholder: "Type something in English…",
    demoTexts: [
      {
        label: "Greeting",
        text: "Hello, how are you? I hope you are having a wonderful day.",
      },
      {
        label: "Find a hospital",
        text: "Could you please tell me how to get to the nearest hospital from here?",
      },
      {
        label: "Request water",
        text: "I would like a glass of water and something light to eat, please.",
      },
    ],
  },
  "hi-to-en": {
    source: "हिन्दी",
    target: "English",
    targetCode: "en",
    sourcePill: "हिन्दी · HINDI",
    targetPill: "ENGLISH",
    placeholder: "हिन्दी में कुछ लिखें…",
    demoTexts: [
      {
        label: "अभिवादन",
        text: "नमस्ते, आप कैसे हैं? आशा है कि आपका दिन बहुत अच्छा जा रहा है।",
      },
      {
        label: "अस्पताल पूछें",
        text: "क्या आप कृपया बता सकते हैं कि यहाँ से नजदीकी अस्पताल कैसे पहुँचा जा सकता है?",
      },
      {
        label: "पानी माँगें",
        text: "मुझे कृपया एक गिलास पानी और खाने के लिए कुछ हल्का चाहिए।",
      },
    ],
  },
};

const supportedAudioTypes = new Set([
  "audio/flac",
  "audio/mp4",
  "audio/mpeg",
  "audio/ogg",
  "audio/wav",
  "audio/webm",
]);

let activeRequestId = 0;
let activeController: AbortController | null = null;
let speechRequestId = 0;
let speechController: AbortController | null = null;
let speechProcessing = false;
let mediaStream: MediaStream | null = null;
let mediaRecorder: MediaRecorder | null = null;
let recordingChunks: Blob[] = [];
let capturedAudio: Blob | null = null;
let recordingSessionId = 0;
let recordingActive = false;
let recordingFinalizing = false;
let requestingMicrophone = false;
let translatedAudioUrl: string | null = null;

function setRecordingStatus(message: string, state = "info") {
  recordingStatus.textContent = message;
  recordingStatus.dataset.state = state;
}

function stopMediaTracks(stream: MediaStream | null) {
  if (!stream) return;
  for (const track of stream.getTracks()) {
    track.stop();
  }
}

function stopMediaRecorder(recorder: MediaRecorder | null) {
  if (!recorder || recorder.state === "inactive") return true;
  try {
    recorder.stop();
    return true;
  } catch (error) {
    console.warn("The microphone recorder could not be stopped cleanly.", error);
    return false;
  }
}

function updateRecordingControls() {
  recordButton.disabled = recordingActive || recordingFinalizing || requestingMicrophone;
  stopButton.disabled = !recordingActive;
  stopButton.title = recordingActive ? "Stop microphone recording" : "No recording is in progress";
  recordingIndicator.classList.toggle("is-recording", recordingActive);
  speechSubmitButton.disabled =
    !(capturedAudio instanceof Blob) ||
    speechProcessing ||
    activeController !== null ||
    recordingActive ||
    recordingFinalizing;
}

function microphoneErrorMessage(error: { name?: string } | null) {
  if (error?.name === "NotAllowedError" || error?.name === "SecurityError") {
    return "Microphone access was blocked. Allow microphone access for this site in your browser settings, then try again.";
  }
  if (error?.name === "NotFoundError" || error?.name === "DevicesNotFoundError") {
    return "No microphone was found. Connect a microphone and try again.";
  }
  if (error?.name === "NotReadableError" || error?.name === "TrackStartError") {
    return "The microphone is unavailable. Close other apps using it and try again.";
  }
  return "Microphone access could not start. Check your browser and device permissions, then try again.";
}

function releaseRecordingResources() {
  const stream = mediaStream;
  mediaStream = null;
  stopMediaTracks(stream);
}

function resetRecording() {
  recordingSessionId += 1;
  requestingMicrophone = false;
  recordingActive = false;
  recordingFinalizing = false;
  recordingChunks = [];
  capturedAudio = null;

  const recorder = mediaRecorder;
  mediaRecorder = null;
  stopMediaRecorder(recorder);
  releaseRecordingResources();
  updateRecordingControls();
}

async function startRecording() {
  if (recordingActive || requestingMicrophone) return;

  if (!navigator.mediaDevices?.getUserMedia || typeof window.MediaRecorder !== "function") {
    setRecordingStatus(
      "Microphone recording needs a supported browser and a secure page (HTTPS or localhost).",
      "error",
    );
    setStatus("Open this page over HTTPS or localhost in a browser that supports audio recording.", "error");
    return;
  }

  const sessionId = ++recordingSessionId;
  cancelTextRequest();
  cancelSpeechRequest();
  clearTranslationOutput();
  requestingMicrophone = true;
  capturedAudio = null;
  setRecordingStatus("Waiting for microphone permission…", "loading");
  updateRecordingControls();

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error) {
    if (sessionId !== recordingSessionId) return;
    requestingMicrophone = false;
    updateRecordingControls();
    const message = microphoneErrorMessage(error);
    setRecordingStatus(message, "error");
    setStatus(message, "error");
    return;
  }

  if (sessionId !== recordingSessionId) {
    stopMediaTracks(stream);
    return;
  }
  if (document.hidden) {
    stopMediaTracks(stream);
    requestingMicrophone = false;
    updateRecordingControls();
    const message = "Recording could not start while this page was hidden. Return here and select Start.";
    setRecordingStatus(message);
    setStatus(message, "info");
    return;
  }

  try {
    const recorder = new window.MediaRecorder(stream);
    mediaStream = stream;
    mediaRecorder = recorder;
    recordingChunks = [];
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data?.size) recordingChunks.push(event.data);
    });
    recorder.addEventListener("error", () => {
      if (sessionId !== recordingSessionId) return;
      resetRecording();
      const message = "Recording stopped unexpectedly. Check microphone access and try again.";
      setRecordingStatus(message, "error");
      setStatus(message, "error");
    });
    recorder.addEventListener("stop", () => {
      if (sessionId !== recordingSessionId) return;
      recordingActive = false;
      recordingFinalizing = false;
      mediaRecorder = null;
      releaseRecordingResources();
      recordingChunks = recordingChunks.filter((chunk) => chunk.size > 0);
      capturedAudio = new Blob(recordingChunks, {
        type: recorder.mimeType || recordingChunks[0]?.type || "audio/webm",
      });
      recordingChunks = [];
      updateRecordingControls();

      if (!capturedAudio.size) {
        capturedAudio = null;
        const message = "No audio was captured. Check your microphone and try again.";
        setRecordingStatus(message, "error");
        setStatus(message, "error");
        return;
      }

      setRecordingStatus("Recording ready. Your audio stays in this browser.", "success");
      setStatus("Recording ready. You can start another recording when needed.", "success");
    });
    recorder.start();
    requestingMicrophone = false;
    recordingActive = true;
    updateRecordingControls();
    setRecordingStatus("Recording… Select Stop when you’re finished.", "recording");
    setStatus("Microphone recording is active.", "recording");
  } catch (error) {
    if (sessionId === recordingSessionId) {
      mediaStream = stream;
      resetRecording();
      const message = microphoneErrorMessage(error);
      setRecordingStatus(message, "error");
      setStatus(message, "error");
    } else {
      stopMediaTracks(stream);
    }
  }
}

function stopRecording() {
  if (!mediaRecorder || !recordingActive) return;
  const recorder = mediaRecorder;
  recordingActive = false;
  recordingFinalizing = true;
  updateRecordingControls();
  setRecordingStatus("Finishing recording…", "loading");
  setStatus("Finishing microphone recording…", "loading");
  if (!stopMediaRecorder(recorder)) {
    mediaRecorder = null;
    resetRecording();
    const message = "Recording could not be finalized. Check microphone access and try again.";
    setRecordingStatus(message, "error");
    setStatus(message, "error");
    return;
  }
  releaseRecordingResources();
}

function updateDirection() {
  const direction = directions[directionSelect.value];
  sourceLanguage.textContent = direction.source;
  targetLanguage.textContent = direction.target;
  targetLanguage.lang = direction.targetCode;
  sourcePill.textContent = direction.sourcePill;
  targetPill.textContent = direction.targetPill;
  sourceText.placeholder = direction.placeholder;
  demoTextSelect.replaceChildren(new Option("Try demo text…", ""));
  for (const demo of direction.demoTexts) {
    demoTextSelect.add(new Option(demo.label, demo.text));
  }
  updateInput();
}

function setInputMode(mode: "text" | "voice") {
  const isTextMode = mode === "text";
  textModeButton.setAttribute("aria-pressed", String(isTextMode));
  voiceModeButton.setAttribute("aria-pressed", String(!isTextMode));
  textInputMode.hidden = !isTextMode;
  voiceInputMode.hidden = isTextMode;
}

function updateInput() {
  characterCount.textContent = `${sourceText.value.length} / ${sourceText.maxLength}`;
  translateButton.disabled =
    sourceText.value.trim().length === 0 ||
    translateButton.classList.contains("is-loading") ||
    speechProcessing ||
    activeController !== null;
}

function setStatus(message: string, state = "info") {
  workspaceStatusText.textContent = message;
  workspaceStatus.dataset.state = state;
  workspaceStatusIcon.textContent =
    { loading: "…", success: "✓", error: "!", recording: "●" }[state] || "i";
}

function updateAudioControls() {
  const hasAudio = translatedAudioUrl !== null;
  const isPlaying = hasAudio && !translatedAudio.paused && !translatedAudio.ended;
  audioToggleButton.disabled = !hasAudio;
  audioToggleButton.setAttribute(
    "aria-label",
    isPlaying ? "Pause translated audio" : "Play translated audio",
  );
  audioToggleButton.title = isPlaying ? "Pause translated audio" : "Play translated audio";
  audioToggleLabel.textContent = isPlaying ? "Pause" : "Play";
  const audioToggleIcon = audioToggleButton.querySelector("span");
  if (audioToggleIcon) audioToggleIcon.textContent = isPlaying ? "Ⅱ" : "▶";
  audioReplayButton.disabled = !hasAudio;
  audioReplayButton.title = hasAudio
    ? "Replay translated audio"
    : "No translated audio is available";
}

function releaseTranslatedAudio() {
  const previousUrl = translatedAudioUrl;
  translatedAudioUrl = null;
  translatedAudio.pause();
  translatedAudio.removeAttribute("src");
  translatedAudio.load();
  if (previousUrl) URL.revokeObjectURL(previousUrl);
  audioStatus.textContent = "Generated audio will appear here";
  updateAudioControls();
}

function setTranslatedAudio(audioBlob: Blob) {
  releaseTranslatedAudio();
  translatedAudioUrl = URL.createObjectURL(audioBlob);
  translatedAudio.src = translatedAudioUrl;
  translatedAudio.load();
  audioStatus.textContent = "Generated audio is ready. Select Play to listen.";
  updateAudioControls();
}

function playbackErrorMessage(error: { name?: string } | null) {
  if (error?.name === "NotAllowedError") {
    return "The browser blocked audio playback. Select Play again to retry.";
  }
  if (error?.name === "NotSupportedError") {
    return "This browser cannot play the generated audio format. Try another browser or regenerate it.";
  }
  return "Translated audio playback failed. Try again or regenerate the translation.";
}

function reportAudioElementError() {
  if (!translatedAudioUrl || !translatedAudio.error) return;
  const messages: Record<number, string> = {
    2: "Generated audio could not be loaded. Check your connection and try the translation again.",
    3: "Generated audio could not be decoded. Try another browser or regenerate the translation.",
    4: "This browser cannot play the generated audio format. Try another browser or regenerate it.",
  };
  const message =
    messages[translatedAudio.error?.code] ||
    "Generated audio could not be played. Try another browser or regenerate the translation.";
  audioStatus.textContent = message;
  setStatus(message, "error");
  updateAudioControls();
}

async function playTranslatedAudio(restart = false) {
  const audioUrl = translatedAudioUrl;
  if (!audioUrl) return;
  try {
    if (restart) translatedAudio.currentTime = 0;
    await translatedAudio.play();
  } catch (error) {
    if (audioUrl !== translatedAudioUrl) return;
    const message = playbackErrorMessage(error);
    audioStatus.textContent = message;
    setStatus(message, "error");
    updateAudioControls();
  }
}

function toggleTranslatedAudio() {
  if (!translatedAudioUrl) return;
  if (!translatedAudio.paused && !translatedAudio.ended) {
    translatedAudio.pause();
    return;
  }
  playTranslatedAudio();
}

function getApiUrl(endpoint = "translate"): string {
  return `/api/${endpoint}`;
}

function clearTranslationOutput() {
  releaseTranslatedAudio();
  placeholderContent.hidden = false;
  translationOutput.hidden = true;
  sourceOutput.textContent = "";
  translatedOutput.textContent = "";
}

function resetWorkspace() {
  cancelTextRequest();
  cancelSpeechRequest();
  resetRecording();
  sourceText.value = "";
  updateInput();
  clearTranslationOutput();
  setRecordingStatus("Choose Start to allow microphone access");
  setStatus("Workspace reset. Ready to translate.", "info");
}

function cancelSpeechRequest() {
  speechRequestId += 1;
  if (speechController) speechController.abort();
  speechController = null;
  speechProcessing = false;
  releaseTranslatedAudio();
  speechSubmitButton.classList.remove("is-loading");
  speechSubmitLabel.textContent = "Translate recording";
  updateRecordingControls();
  updateInput();
}

function cancelTextRequest() {
  activeRequestId += 1;
  if (activeController) activeController.abort();
  activeController = null;
  translateButton.classList.remove("is-loading");
  translateButtonLabel.textContent = "Translate text";
  updateInput();
  updateRecordingControls();
}

function decodeMetadataHeader(response: Response, name: string): string | null {
  const value = response.headers.get(name);
  if (!value) return null;
  try {
    return decodeURIComponent(value);
  } catch {
    throw new Error("The speech service returned invalid text metadata. Please retry.");
  }
}

async function getApiError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return typeof data?.message === "string" && data.message.trim()
      ? data.message
      : "Speech processing could not be completed. Please retry.";
  } catch {
    return "Speech processing could not be completed. Please retry.";
  }
}

async function synthesizeTranslatedText(
  text: string,
  targetLanguage: string,
  signal: AbortSignal,
): Promise<Blob> {
  const response = await fetch(getApiUrl("text-to-speech"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, target_language: targetLanguage }),
    signal,
  });
  if (!response.ok) throw new Error(await getApiError(response));

  const contentType = response.headers
    .get("Content-Type")
    ?.split(";", 1)[0]
    .trim()
    .toLowerCase();
  if (!contentType || !supportedAudioTypes.has(contentType)) {
    throw new Error("The speech service returned an unsupported audio format.");
  }

  const audioBlob = await response.blob();
  if (!audioBlob.size) {
    throw new Error("The speech service returned an empty audio file.");
  }
  return new Blob([audioBlob], { type: contentType });
}

async function translateRecording() {
  if (speechProcessing || activeController) return;
  if (!(capturedAudio instanceof Blob)) {
    setStatus("Record audio and stop the recording before submitting it.", "error");
    return;
  }

  const audio = capturedAudio;
  const direction = directionSelect.value;
  const requestId = ++speechRequestId;
  releaseTranslatedAudio();
  const controller = new AbortController();
  speechController = controller;
  speechProcessing = true;
  speechSubmitButton.classList.add("is-loading");
  speechSubmitLabel.textContent = "Processing recording…";
  updateRecordingControls();
  updateInput();
  placeholderContent.hidden = true;
  translationOutput.hidden = false;
  sourceOutput.textContent = "Waiting for source transcript…";
  translatedOutput.textContent = "Waiting for translation…";
  setStatus("Uploading recording and processing speech…", "loading");

  const formData = new FormData();
  let receivedMetadata = false;
  const mediaType = (audio.type || "audio/webm").split(";", 1)[0].toLowerCase();
  const extensions: Record<string, string> = {
    "audio/flac": "flac",
    "audio/mp4": "mp4",
    "audio/mpeg": "mp3",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/webm": "webm",
  };
  formData.append("file", audio, `recording.${extensions[mediaType] || "webm"}`);
  formData.append("direction", direction);

  try {
    const response = await fetch(getApiUrl("speech-translate"), {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    if (requestId !== speechRequestId) return;
    if (!response.ok) throw new Error(await getApiError(response));

    const transcript = decodeMetadataHeader(response, "X-Transcript");
    const translation = decodeMetadataHeader(response, "X-Translated-Text");
    if (!transcript?.trim() || !translation?.trim()) {
      throw new Error("The speech service returned incomplete text metadata. Please retry.");
    }

    sourceOutput.textContent = transcript;
    sourceOutput.lang = direction === "hi-to-en" ? "hi" : "en";
    translatedOutput.textContent = translation;
    translatedOutput.lang = direction === "en-to-hi" ? "hi" : "en";
    receivedMetadata = true;

    const contentType = response.headers
      .get("Content-Type")
      ?.split(";", 1)[0]
      .trim()
      .toLowerCase();
    if (!contentType || !supportedAudioTypes.has(contentType)) {
      throw new Error("The speech service returned an unsupported audio format. Please retry.");
    }
    const audioBlob = await response.blob();
    if (requestId !== speechRequestId) return;
    if (!audioBlob.size) {
      throw new Error("The speech service returned an empty audio file. Please retry.");
    }

    setTranslatedAudio(new Blob([audioBlob], { type: contentType }));
    audioStatus.textContent = "Generated audio is ready. Select Play to listen.";
    setStatus("Speech translation complete. Source transcript and translation are shown separately.", "success");
  } catch (error) {
    if ((error instanceof Error && error.name === "AbortError") || requestId !== speechRequestId) {
      return;
    }
    if (!receivedMetadata) {
      sourceOutput.textContent = "Transcript unavailable";
      translatedOutput.textContent = "Translation unavailable";
    }
    releaseTranslatedAudio();
    audioStatus.textContent =
      error instanceof Error ? error.message : "Translated audio could not be generated. Please retry.";
    setStatus(
      error instanceof Error
        ? `${error.message} Your recording is available to retry.`
        : "Speech processing failed. Your recording is available to retry.",
      "error",
    );
  } finally {
    if (requestId === speechRequestId) {
      speechController = null;
      speechProcessing = false;
      speechSubmitButton.classList.remove("is-loading");
      speechSubmitLabel.textContent = "Translate recording";
      updateRecordingControls();
      updateInput();
    }
  }
}

async function translateText() {
  if (activeController || speechProcessing) return;
  const source = sourceText.value.trim();
  if (!source) {
    setStatus("Enter text before translating.", "error");
    return;
  }

  cancelSpeechRequest();
  releaseTranslatedAudio();

  const requestId = ++activeRequestId;
  const controller = new AbortController();
  activeController = controller;
  translateButton.classList.add("is-loading");
  translateButton.disabled = true;
  translateButtonLabel.textContent = "Translating…";
  updateRecordingControls();
  placeholderContent.hidden = true;
  translationOutput.hidden = false;
  sourceOutput.textContent = source;
  translatedOutput.textContent = "Translating…";
  setStatus("Translating your text locally…", "loading");

  try {
    const response = await fetch(getApiUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction: directionSelect.value, source_text: source }),
      signal: controller.signal,
    });
    const data = await response.json().catch(() => null);

    if (requestId !== activeRequestId) return;
    if (!response.ok) throw new Error(data?.message || "Translation could not be completed.");
    if (typeof data?.translated_text !== "string" || !data.translated_text.trim()) {
      throw new Error("The translation service returned no text.");
    }

    translatedOutput.textContent = data.translated_text;
    translatedOutput.lang = data.target_language === "hi" ? "hi" : "en";
    translateButtonLabel.textContent = "Generating audio…";
    audioStatus.textContent = "Generating audio…";
    setStatus("Translation complete. Generating speech…", "loading");
    try {
      const audioBlob = await synthesizeTranslatedText(
        data.translated_text,
        data.target_language,
        controller.signal,
      );
      if (requestId !== activeRequestId) return;
      setTranslatedAudio(audioBlob);
      setStatus("Translation and speech synthesis complete.", "success");
    } catch (error) {
      if ((error instanceof Error && error.name === "AbortError") || requestId !== activeRequestId) {
        return;
      }
      releaseTranslatedAudio();
      const message =
        error instanceof Error ? error.message : "Speech synthesis could not be completed.";
      audioStatus.textContent = message;
      setStatus("Translation complete, but speech could not be generated.", "error");
    }
  } catch (error) {
    if (error.name === "AbortError" || requestId !== activeRequestId) return;
    sourceOutput.textContent = source;
    translatedOutput.textContent = "Translation unavailable";
    setStatus(error instanceof Error ? error.message : "Translation could not be completed.", "error");
  } finally {
    if (requestId === activeRequestId) {
      translateButton.classList.remove("is-loading");
      translateButtonLabel.textContent = "Translate text";
      activeController = null;
      updateInput();
      updateRecordingControls();
    }
  }
}

directionSelect.addEventListener("change", () => {
  cancelTextRequest();
  cancelSpeechRequest();
  resetRecording();
  updateDirection();
  placeholderContent.hidden = false;
  translationOutput.hidden = true;
  sourceOutput.textContent = "";
  translatedOutput.textContent = "";
  setRecordingStatus("Choose Start to allow microphone access");
  setStatus("Direction changed. Ready to translate.", "info");
});
textModeButton.addEventListener("click", () => setInputMode("text"));
voiceModeButton.addEventListener("click", () => setInputMode("voice"));
sourceText.addEventListener("input", () => {
  demoTextSelect.value = "";
  updateInput();
  if (workspaceStatus.dataset.state === "error" || workspaceStatus.dataset.state === "success") {
    setStatus("Ready to translate.", "info");
  }
});
demoTextSelect.addEventListener("change", () => {
  if (!demoTextSelect.value) return;
  sourceText.value = demoTextSelect.value;
  updateInput();
  setStatus("Demo text loaded. Ready to translate.", "info");
});
translateButton.addEventListener("click", translateText);
speechSubmitButton.addEventListener("click", translateRecording);
resetButton.addEventListener("click", resetWorkspace);
recordButton.addEventListener("click", startRecording);
stopButton.addEventListener("click", stopRecording);
audioToggleButton.addEventListener("click", toggleTranslatedAudio);
audioReplayButton.addEventListener("click", () => playTranslatedAudio(true));
translatedAudio.addEventListener("play", () => {
  if (!translatedAudioUrl || translatedAudio.paused || translatedAudio.ended) return;
  audioStatus.textContent = "Playing translated audio.";
  updateAudioControls();
});
translatedAudio.addEventListener("pause", () => {
  if (!translatedAudioUrl || translatedAudio.ended || !translatedAudio.paused) return;
  audioStatus.textContent = "Playback paused. Select Play to continue.";
  updateAudioControls();
});
translatedAudio.addEventListener("ended", () => {
  if (!translatedAudioUrl || !translatedAudio.ended) return;
  audioStatus.textContent = "Playback finished. Select Replay to listen again.";
  updateAudioControls();
});
translatedAudio.addEventListener("error", reportAudioElementError);
window.addEventListener("pagehide", () => {
  const wasCapturing = recordingActive || requestingMicrophone;
  cancelTextRequest();
  cancelSpeechRequest();
  resetRecording();
  if (wasCapturing) {
    const message = "Recording stopped when this page was left. Select Start to record again.";
    setRecordingStatus(message);
    setStatus(message, "info");
  }
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) return;
  const wasCapturing = recordingActive || requestingMicrophone;
  const wasProcessing = speechProcessing || activeController !== null;
  cancelTextRequest();
  cancelSpeechRequest();
  resetRecording();
  if (wasProcessing) {
    clearTranslationOutput();
    setStatus("Processing stopped because this page was hidden. Submit again to retry.", "info");
  }
  if (wasCapturing) {
    const message = "Recording stopped when this page was hidden. Select Start to record again.";
    setRecordingStatus(message);
    setStatus(message, "info");
  }
});

updateDirection();
updateRecordingControls();
updateAudioControls();
