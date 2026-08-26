// Content Script injecting PyTorch AI Agent into live agar.io tab
console.log("🎮 Agar.io MARL AI Controller Extension Active!");

let socket = null;
let isConnected = false;
let hudElement = null;

// Track intercepted entities from canvas draw operations (stored in relative game units)
let frameFood = [];
let frameViruses = [];
let frameOpponents = [];
let playerRadius = 20.0; // Default starting radius

// Create On-Screen AI Control HUD Badge
function createHud() {
  if (document.getElementById("ai-bot-hud")) return;
  hudElement = document.createElement("div");
  hudElement.id = "ai-bot-hud";
  hudElement.style.position = "fixed";
  hudElement.style.top = "15px";
  hudElement.style.left = "15px";
  hudElement.style.zIndex = "999999";
  hudElement.style.background = "rgba(15, 23, 42, 0.88)";
  hudElement.style.backdropFilter = "blur(10px)";
  hudElement.style.border = "1px solid rgba(56, 189, 248, 0.5)";
  hudElement.style.color = "#f8fafc";
  hudElement.style.padding = "10px 16px";
  hudElement.style.borderRadius = "12px";
  hudElement.style.fontFamily = "Outfit, sans-serif";
  hudElement.style.fontSize = "13px";
  hudElement.style.boxShadow = "0 4px 20px rgba(0,0,0,0.5)";
  hudElement.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;">
      <span id="ai-status-dot" style="width:10px;height:10px;border-radius:50%;background:#ef4444;"></span>
      <strong style="color:#38bdf8;">Agar.io PyTorch AI Agent</strong>
    </div>
    <div id="ai-action-text" style="margin-top:4px;font-size:11px;color:#94a3b8;">Connecting to ws://127.0.0.1:8081...</div>
  `;
  document.body.appendChild(hudElement);
}

function updateHud(isGreen, actionText) {
  const dot = document.getElementById("ai-status-dot");
  const txt = document.getElementById("ai-action-text");
  if (dot) dot.style.background = isGreen ? "#4ade80" : "#ef4444";
  if (txt) txt.innerText = actionText;
}

if (document.body) {
  createHud();
} else {
  document.addEventListener("DOMContentLoaded", createHud);
}

// Establish Direct WebSocket connection to Local Loopback (Exempt from HTTPS CSP mixed content rules)
function connectToPythonInferenceServer() {
  socket = new WebSocket("ws://127.0.0.1:8081");

  socket.onopen = () => {
    console.log("✅ Connected directly to PyTorch Policy Server (ws://127.0.0.1:8081)");
    isConnected = true;
    updateHud(true, "AI Active (ws://127.0.0.1:8081)");
  };

  socket.onmessage = (event) => {
    try {
      const response = JSON.parse(event.data);
      if (response.type === "action" && response.action) {
        window.AgarioInputController.executeAction(response.action);
        const [dx, dy, split, eject] = response.action;
        updateHud(
          true,
          `Action: dx=${dx.toFixed(2)}, dy=${dy.toFixed(2)} | Food:${frameFood.length} | Vir:${frameViruses.length} | Opp:${frameOpponents.length}`
        );
      }
    } catch (e) {
      console.error("Error processing AI action:", e);
    }
  };

  socket.onclose = () => {
    console.warn("WebSocket closed. Retrying in 2 seconds...");
    isConnected = false;
    updateHud(false, "Disconnected from Python Server. Retrying...");
    setTimeout(connectToPythonInferenceServer, 2000);
  };

  socket.onerror = (err) => {
    console.error("WebSocket Error:", err);
  };
}

connectToPythonInferenceServer();

// Intercept Canvas rendering calls to extract coordinates in real-time
(function() {
  const orgArc = CanvasRenderingContext2D.prototype.arc;
  CanvasRenderingContext2D.prototype.arc = function(x, y, radius, startAngle, endAngle, counterclockwise) {
    orgArc.call(this, x, y, radius, startAngle, endAngle, counterclockwise);

    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;
    const cx = screenWidth / 2;
    const cy = screenHeight / 2;

    const matrix = this.getTransform();
    const screenX = x * matrix.a + y * matrix.c + matrix.e;
    const screenY = x * matrix.b + y * matrix.d + matrix.f;
    const screenRadius = radius * Math.hypot(matrix.a, matrix.b);

    const scale = Math.hypot(matrix.a, matrix.b) || 1.0;

    // Calculate game-space relative coordinates centered at the player, adjusting for camera zoom scale
    const relX = (screenX - cx) / scale;
    const relY = (screenY - cy) / scale;
    const gameRadius = screenRadius / scale;

    const fillStyle = this.fillStyle || "";
    const colorStr = typeof fillStyle === "string" ? fillStyle.toLowerCase() : "";

    // Classify drawn circles using game-space radius rules
    if (gameRadius > 1 && gameRadius < 12) {
      // Small colorful circles are food pellets
      frameFood.push({ x: relX, y: relY, r: gameRadius });
    } else if (gameRadius >= 18 && gameRadius <= 32 && (colorStr.includes("33") || colorStr.includes("green") || colorStr.includes("22"))) {
      // Green spiky textured circles are viruses
      frameViruses.push({ x: relX, y: relY, r: gameRadius });
    } else if (gameRadius > 12) {
      // Check if this circle is centered on the player center (the screen center)
      const distToCenter = Math.hypot(screenX - cx, screenY - cy);
      if (distToCenter < 18) {
        // Player's own cell
        playerRadius = gameRadius;
      } else {
        // Opponent cell
        frameOpponents.push({ x: relX, y: relY, r: gameRadius, color: colorStr });
      }
    }
  };
})();

// Continuous State Sampling Loop (30 FPS)
setInterval(() => {
  if (!isConnected || !socket || socket.readyState !== WebSocket.OPEN) return;

  const screenWidth = window.innerWidth;
  const screenHeight = window.innerHeight;
  const cx = screenWidth / 2;
  const cy = screenHeight / 2;

  // Deduplicate and filter intercepted entities for the current frame
  const foodList = frameFood.slice(0, 30);
  const virusList = frameViruses.slice(0, 10);
  const oppList = frameOpponents.slice(0, 16);

  const sampleState = {
    type: "live_state",
    timestamp: Date.now(),
    screen_width: screenWidth,
    screen_height: screenHeight,
    cx: cx,
    cy: cy,
    player_radius: playerRadius,
    food: foodList,
    viruses: virusList,
    opponents: oppList
  };

  socket.send(JSON.stringify(sampleState));

  // Clear buffers for the next frame
  frameFood = [];
  frameViruses = [];
  frameOpponents = [];
}, 33);
