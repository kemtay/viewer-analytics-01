const webcamVideo = document.getElementById("webcamVideo");
const canvas = document.getElementById("canvas");
const messagesDiv = document.getElementById("messages");
const debugDiv = document.getElementById("debug");
const startButton = document.getElementById("startButton");

let analyticsStarted = false;
let sendInProgress = false;
let intervalId = null;

startButton.addEventListener("click", startAnalytics);

async function startAnalytics() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false
    });

    webcamVideo.srcObject = stream;
    analyticsStarted = true;
    startButton.disabled = true;
    startButton.innerText = "Analytics Running";

    // Send around 1.4 frames per second.
    // Increase frequency only if your server can handle it.
    intervalId = setInterval(sendFrameForAnalysis, 700);

    messagesDiv.innerText = "Viewer analytics starting...";
  } catch (err) {
    messagesDiv.innerText = "Camera permission denied or unavailable.";
    debugDiv.innerText = String(err);
  }
}

async function sendFrameForAnalysis() {
  if (!analyticsStarted || sendInProgress) return;

  sendInProgress = true;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(webcamVideo, 0, 0, canvas.width, canvas.height);

  const imageData = canvas.toDataURL("image/jpeg", 0.7);

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        image: imageData
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    messagesDiv.innerText = result.messages.join("\n");

    const headText = result.head
      ? `head_x=${result.head.head_x}, head_y=${result.head.head_y}`
      : "head=N/A";

    debugDiv.innerText = `EAR=${result.ear} | ${headText}`;
  } catch (err) {
    messagesDiv.innerText = "Server error";
    debugDiv.innerText = String(err);
  } finally {
    sendInProgress = false;
  }
}
