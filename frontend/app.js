"use strict";

const directionSelect = document.querySelector("#direction");
const sourceLanguage = document.querySelector("#source-language");
const targetLanguage = document.querySelector("#target-language");
const sourcePill = document.querySelector("#source-pill");
const targetPill = document.querySelector("#target-pill");
const sourceText = document.querySelector("#source-text");
const characterCount = document.querySelector("#character-count");
const translateButton = document.querySelector("#translate-button");
const translateButtonLabel = document.querySelector("#translate-button-label");
const placeholderContent = document.querySelector("#result-placeholder-content");
const translationOutput = document.querySelector("#translation-output");
const sourceOutput = document.querySelector("#source-output");
const translatedOutput = document.querySelector("#translated-output");
const workspaceStatus = document.querySelector("#workspace-status");
const workspaceStatusText = document.querySelector("#workspace-status-text");
const recordButton = document.querySelector("#record-button");
const stopButton = document.querySelector("#stop-button");
const recordingStatus = document.querySelector("#recording-status");
const recordingIndicator = document.querySelector("#recording-indicator");
const speechSubmitButton = document.querySelector("#speech-submit-button");
const speechSubmitLabel = document.querySelector("#speech-submit-label");

const directions = {
  "en-to-hi": {
    source: "English",
    target: "हिन्दी",
    targetCode: "hi",
    sourcePill: "ENGLISH",
    targetPill: "हिन्दी · HINDI",
    placeholder: "Type something in English…",
  },
  "hi-to-en": {
    source: "हिन्दी",
    target: "English",
    targetCode: "en",
    sourcePill: "हिन्दी · HINDI",
    targetPill: "ENGLISH",
    placeholder: "हिन्दी में कुछ लिखें…",
  },
};

let activeRequestId = 0;
let activeController = null;
let speechRequestId = 0;
let speechController = null;
let speechProcessing = false;
let mediaStream = null;
let mediaRecorder = null;
let recordingChunks = [];
let capturedAudio = null;
let recordingSessionId = 0;
let recordingActive = false;
let recordingFinalizing = false;
let requestingMicrophone = false;

function setRecordingStatus(message, state = "info") {
  recordingStatus.textContent = message;
  recordingStatus.dataset.state = state;
}

function stopMediaTracks(stream) {
  if (!stream) return;
  for (const track of stream.getTracks()) {
    track.stop();
  }
}

function stopMediaRecorder(recorder) {
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
    !(capturedAudio instanceof Blob) || speechProcessing || recordingActive || recordingFinalizing;
}

function microphoneErrorMessage(error) {
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
  updateInput();
}

function updateInput() {
  characterCount.textContent = `${sourceText.value.length} / ${sourceText.maxLength}`;
  translateButton.disabled =
    sourceText.value.trim().length === 0 ||
    translateButton.classList.contains("is-loading") ||
    speechProcessing;
}

function setStatus(message, state = "info") {
  workspaceStatusText.textContent = message;
  workspaceStatus.dataset.state = state;
}

function getApiUrl(endpoint = "translate") {
  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
    if (isLocalHost && window.location.port !== "8000") {
      return `http://${window.location.hostname}:8000/api/${endpoint}`;
    }
    return `${window.location.origin}/api/${endpoint}`;
  }
  return `http://127.0.0.1:8000/api/${endpoint}`;
}

function clearTranslationOutput() {
  placeholderContent.hidden = false;
  translationOutput.hidden = true;
  sourceOutput.textContent = "";
  translatedOutput.textContent = "";
}

function cancelSpeechRequest() {
  speechRequestId += 1;
  if (speechController) speechController.abort();
  speechController = null;
  speechProcessing = false;
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
}

function decodeMetadataHeader(response, name) {
  const value = response.headers.get(name);
  if (!value) return null;
  try {
    return decodeURIComponent(value);
  } catch {
    throw new Error("The speech service returned invalid text metadata. Please retry.");
  }
}

async function getApiError(response) {
  try {
    const data = await response.json();
    return typeof data?.message === "string" && data.message.trim()
      ? data.message
      : "Speech processing could not be completed. Please retry.";
  } catch {
    return "Speech processing could not be completed. Please retry.";
  }
}

async function translateRecording() {
  if (!(capturedAudio instanceof Blob) || speechProcessing) {
    setStatus("Record audio and stop the recording before submitting it.", "error");
    return;
  }

  cancelTextRequest();

  const audio = capturedAudio;
  const direction = directionSelect.value;
  const requestId = ++speechRequestId;
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
  const mediaType = (audio.type || "audio/webm").split(";", 1)[0].toLowerCase();
  const extensions = {
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
    setStatus("Speech translation complete. Source transcript and translation are shown separately.", "success");
  } catch (error) {
    if ((error instanceof Error && error.name === "AbortError") || requestId !== speechRequestId) {
      return;
    }
    sourceOutput.textContent = "Transcript unavailable";
    translatedOutput.textContent = "Translation unavailable";
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
  const source = sourceText.value.trim();
  if (!source) {
    setStatus("Enter text before translating.", "error");
    return;
  }

  cancelSpeechRequest();
  if (activeController) activeController.abort();

  const requestId = ++activeRequestId;
  const controller = new AbortController();
  activeController = controller;
  translateButton.classList.add("is-loading");
  translateButton.disabled = true;
  translateButtonLabel.textContent = "Translating…";
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
    setStatus("Translation complete.", "success");
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
sourceText.addEventListener("input", () => {
  updateInput();
  if (workspaceStatus.dataset.state === "error" || workspaceStatus.dataset.state === "success") {
    setStatus("Ready to translate.", "info");
  }
});
translateButton.addEventListener("click", translateText);
speechSubmitButton.addEventListener("click", translateRecording);
recordButton.addEventListener("click", startRecording);
stopButton.addEventListener("click", stopRecording);
window.addEventListener("pagehide", () => {
  const wasCapturing = recordingActive || requestingMicrophone;
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
  resetRecording();
  if (wasCapturing) {
    const message = "Recording stopped when this page was hidden. Select Start to record again.";
    setRecordingStatus(message);
    setStatus(message, "info");
  }
});

updateDirection();
updateRecordingControls();
