// Agar.io MARL Visualizer Client
const canvas = document.getElementById('agario-canvas');
const ctx = canvas.getContext('2d');
const fpsEl = document.getElementById('fps-counter');
const stepEl = document.getElementById('step-counter');
const statusEl = document.getElementById('connection-status');
const leaderboardList = document.getElementById('leaderboard-list');

// Canvas dimensions
canvas.width = 800;
canvas.height = 600;

// Color palette for agents
const AGENT_COLORS = [
  '#38bdf8', '#c084fc', '#4ade80', '#facc15',
  '#f87171', '#fb923c', '#2dd4bf', '#a78bfa',
  '#34d399', '#f472b6', '#60a5fa', '#e879f9',
];

let gameState = null;
let lastFrameTime = performance.now();
let frameCount = 0;
let fps = 60;
let socket = null;

// Safe Chart.js Initialization
let metricsChart = null;
try {
  if (typeof Chart !== 'undefined') {
    const chartCtx = document.getElementById('metrics-chart').getContext('2d');
    metricsChart = new Chart(chartCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Avg Mass',
            data: [],
            borderColor: '#38bdf8',
            borderWidth: 2,
            tension: 0.3,
            pointRadius: 0,
          },
          {
            label: 'Policy Loss',
            data: [],
            borderColor: '#c084fc',
            borderWidth: 2,
            tension: 0.3,
            pointRadius: 0,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }
} catch (err) {
  console.warn("Chart.js failed to initialize:", err);
}

// Fetch Active Config & Connect WebSocket
async function initWebSocket() {
  let wsPort = 8081;
  try {
    const res = await fetch('/config');
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.ws_port) wsPort = cfg.ws_port;
    }
  } catch (e) {
    console.log("Using default ws_port 8081");
  }

  const wsHost = window.location.hostname || 'localhost';
  const wsUrl = `ws://${wsHost}:${wsPort}`;
  console.log(`Connecting to WebSocket at ${wsUrl}`);
  
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("WebSocket Connected!");
    if (statusEl) {
      statusEl.innerText = 'Connected to Engine';
      if (statusEl.previousElementSibling) {
        statusEl.previousElementSibling.className = 'status-dot green';
      }
    }
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'state_update') {
        gameState = data;
        if (stepEl) stepEl.innerText = data.step;
        updateLeaderboard(data.players);
      }
    } catch (e) {
      console.error("Error parsing message:", e);
    }
  };

  socket.onerror = (err) => {
    console.error("WebSocket Error:", err);
  };

  socket.onclose = () => {
    console.warn("WebSocket Connection Closed. Retrying in 2s...");
    if (statusEl) {
      statusEl.innerText = 'Disconnected';
      if (statusEl.previousElementSibling) {
        statusEl.previousElementSibling.className = 'status-dot red';
      }
    }
    setTimeout(initWebSocket, 2000);
  };
}

initWebSocket();

function updateLeaderboard(players) {
  if (!players || !leaderboardList) return;
  const totals = [];
  Object.keys(players).forEach((agentId, index) => {
    const cells = players[agentId];
    const totalMass = cells.reduce((sum, c) => sum + c.mass, 0);
    totals.push({ agentId, totalMass, color: AGENT_COLORS[index % AGENT_COLORS.length] });
  });

  totals.sort((a, b) => b.totalMass - a.totalMass);

  leaderboardList.innerHTML = '';
  totals.slice(0, 5).forEach((item) => {
    const li = document.createElement('li');
    li.className = 'leaderboard-item';
    li.innerHTML = `
      <div class="agent-name">
        <span class="color-dot" style="background:${item.color}"></span>
        <span>${item.agentId}</span>
      </div>
      <strong>${Math.round(item.totalMass)}</strong>
    `;
    leaderboardList.appendChild(li);
  });
}

// Continuous 60 FPS Render Loop
function renderLoop() {
  renderGame();
  requestAnimationFrame(renderLoop);
}
requestAnimationFrame(renderLoop);

function renderGame() {
  // FPS Counting
  const now = performance.now();
  frameCount++;
  if (now - lastFrameTime >= 1000) {
    fps = frameCount;
    if (fpsEl) fpsEl.innerText = fps;
    frameCount = 0;
    lastFrameTime = now;
  }

  // Clear Canvas
  ctx.fillStyle = '#090d16';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (!gameState) {
    // Waiting for server state screen
    ctx.fillStyle = '#94a3b8';
    ctx.font = '16px Outfit';
    ctx.textAlign = 'center';
    ctx.fillText('Connecting to Agar.io Engine...', canvas.width / 2, canvas.height / 2);
    return;
  }

  const mapWidth = gameState.map_width || 2000;
  const mapHeight = gameState.map_height || 2000;
  const scaleX = canvas.width / mapWidth;
  const scaleY = canvas.height / mapHeight;

  // Render Grid Lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
  ctx.lineWidth = 1;
  const gridSize = 100 * scaleX;
  for (let x = 0; x < canvas.width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y < canvas.height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }

  // Render Food Pellets
  if (gameState.food) {
    ctx.fillStyle = '#64748b';
    gameState.food.forEach((f) => {
      ctx.beginPath();
      ctx.arc(f.x * scaleX, f.y * scaleY, 2.5, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  // Render Viruses
  if (gameState.viruses) {
    ctx.fillStyle = '#10b981';
    ctx.strokeStyle = '#059669';
    ctx.lineWidth = 3;
    gameState.viruses.forEach((v) => {
      ctx.beginPath();
      ctx.arc(v.x * scaleX, v.y * scaleY, v.radius * scaleX, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });
  }

  // Render Ejected Mass
  if (gameState.ejected) {
    ctx.fillStyle = '#f59e0b';
    gameState.ejected.forEach((em) => {
      ctx.beginPath();
      ctx.arc(em.x * scaleX, em.y * scaleY, 4, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  // Render Player Cells
  if (gameState.players) {
    Object.keys(gameState.players).forEach((agentId, index) => {
      const color = AGENT_COLORS[index % AGENT_COLORS.length];
      const cells = gameState.players[agentId];

      cells.forEach((c) => {
        const cx = c.x * scaleX;
        const cy = c.y * scaleY;
        const r = Math.max(4, c.radius * scaleX);

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Mass label
        if (r > 10) {
          ctx.fillStyle = '#ffffff';
          ctx.font = 'bold 11px Outfit';
          ctx.textAlign = 'center';
          ctx.fillText(Math.round(c.mass), cx, cy + 4);
        }
      });
    });
  }
}
