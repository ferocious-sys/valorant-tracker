"use strict";

const hudState = makeHudState();
window.hudState = hudState;
let hudWindow = null;
let hudHeld = false;
let registered = false;
const statusElement = document.getElementById("feed-status");

function sendSnapshot() {
  if (!hudWindow) return;
  overwolf.windows.sendMessage(hudWindow.id, "snapshot", hudState.snapshot(), () => {});
}

function showHud() {
  hudHeld = true;
  overwolf.windows.obtainDeclaredWindow("hud", result => {
    if (!result || !result.success) return;
    hudWindow = result.window;
    overwolf.windows.restore(hudWindow.id, () => {
      if (!hudHeld) {
        overwolf.windows.hide(hudWindow.id, () => {});
        return;
      }
      sendSnapshot();
    });
  });
}

function hideHud() {
  hudHeld = false;
  if (hudWindow) overwolf.windows.hide(hudWindow.id, () => {});
}

overwolf.settings.hotkeys.onHold.addListener(event => {
  if (event.name !== "hold_hud") return;
  if (event.state === "down") showHud();
  if (event.state === "up") hideHud();
});

overwolf.games.events.onInfoUpdates2.addListener(event => {
  hudState.ingestEvent(event);
  statusElement.textContent = hudState.snapshot().round ?
    `VALORANT live feed active · round ${hudState.snapshot().round}` : "Connected. Waiting for a VALORANT match.";
  if (hudHeld) sendSnapshot();
});

overwolf.games.events.onError.addListener(error => {
  console.warn("VALORANT game-event feed:", error.reason);
  statusElement.textContent = "Game feed unavailable. Check Overwolf's VALORANT overlay settings.";
});

function subscribe() {
  if (registered) return;
  overwolf.games.events.setRequiredFeatures(["me", "match_info"], result => {
    if (!result || !result.success) {
      console.warn("VALORANT game-event features unavailable:", result && result.error);
      statusElement.textContent = "Waiting for VALORANT game events.";
      return;
    }
    registered = true;
    statusElement.textContent = "Connected. Waiting for a VALORANT match.";
    console.log("VALORANT Tracker HUD listening for personal game events.");
  });
}

subscribe();
