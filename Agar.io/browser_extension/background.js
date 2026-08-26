// Background Service Worker for Manifest V3 Chrome Extension
// Bypasses HTTPS Mixed Content CSP restrictions by connecting to ws://127.0.0.1:8081 from background thread.

let socket = null;
let isWsConnected = false;
let activeTabId = null;

function connectWebSocket() {
  socket = new WebSocket("ws://127.0.0.1:8081");

  socket.onopen = () => {
    console.log("✅ Service Worker connected to ws://127.0.0.1:8081");
    isWsConnected = true;
    notifyTab({ type: "ws_status", connected: true });
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "action" && activeTabId) {
        chrome.tabs.sendMessage(activeTabId, data).catch(() => {});
      }
    } catch (e) {
      console.error("Error parsing WebSocket message:", e);
    }
  };

  socket.onerror = (err) => {
    console.error("Service Worker WebSocket Error:", err);
  };

  socket.onclose = () => {
    console.warn("WebSocket disconnected. Retrying in 2 seconds...");
    isWsConnected = false;
    notifyTab({ type: "ws_status", connected: false });
    setTimeout(connectWebSocket, 2000);
  };
}

function notifyTab(msg) {
  if (activeTabId) {
    chrome.tabs.sendMessage(activeTabId, msg).catch(() => {});
  }
}

connectWebSocket();

// Listen for state messages from content_script.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (sender.tab) {
    activeTabId = sender.tab.id;
  }

  if (request.type === "live_state" && isWsConnected && socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(request));
  } else if (request.type === "get_status") {
    sendResponse({ connected: isWsConnected });
  }
  return true;
});
