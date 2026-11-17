// Workaround for anomalyco/opencode#60839 (fix pending in PR #59543): after a
// reconnect, the session view re-syncs the open session and, on any failure,
// including transient transport errors right after a macOS DarkWake, it
// navigates home. This reopens the session when that happens without user
// input, and holds a caffeinate assertion for the TUI's lifetime to cut down
// on idle-sleep wakes. Delete once the upstream fix ships.
//
// Opt out of caffeinate with OPENCODE_CAFFEINATE=0.

import { spawn } from "node:child_process";

const POLL_MS = 250;
// A gap this long between poll ticks means the process was suspended (sleep).
const WAKE_GAP_MS = 5_000;
// Only act on a session -> home transition this soon after a reconnect or wake.
const RECOVERY_WINDOW_MS = 30_000;
// A keypress this recent means the user navigated home on purpose.
const USER_INPUT_GRACE_MS = 3_000;
const RETRY_DELAYS_MS = [0, 1_000, 2_000, 4_000, 8_000, 15_000, 30_000];

export default {
  id: "dotfiles.session-keeper",
  setup,
};

function setup(api) {
  const cleanups = [];
  let disposed = false;

  if (process.platform === "darwin" && process.env.OPENCODE_CAFFEINATE !== "0") {
    try {
      // -i: no idle sleep; -s: no system sleep on AC. -w exits with this TUI.
      const child = spawn("/usr/bin/caffeinate", ["-is", "-w", String(process.pid)], {
        stdio: "ignore",
      });
      child.on("error", () => {});
      child.unref();
      cleanups.push(() => child.kill());
    } catch {}
  }

  let lastSessionID;
  let lastWasSession = false;
  let disruptedAt = 0;
  let lastKeyAt = 0;
  let lastTick = Date.now();
  let restoring;
  const deleted = new Set();

  const onKey = () => {
    lastKeyAt = Date.now();
  };
  const keyInput = api.renderer?.keyInput;
  if (keyInput?.on) {
    keyInput.on("keypress", onKey);
    cleanups.push(() => keyInput.off?.("keypress", onKey));
  }

  cleanups.push(
    api.data.listen(({ details: event }) => {
      if (event.type === "server.connected") disruptedAt = Date.now();
      if (event.type === "session.deleted" && typeof event.data?.sessionID === "string") {
        deleted.add(event.data.sessionID);
      }
    }),
  );

  function route() {
    try {
      return api.ui.router.current();
    } catch {
      return undefined;
    }
  }

  function userActedSince(time) {
    return lastKeyAt >= time - USER_INPUT_GRACE_MS;
  }

  async function restore(sessionID, startedAt) {
    for (const delay of RETRY_DELAYS_MS) {
      if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
      if (disposed || route()?.type !== "home" || userActedSince(startedAt)) return;
      if (deleted.has(sessionID)) return;
      try {
        await api.data.session.sync(sessionID);
      } catch {
        continue;
      }
      if (disposed || route()?.type !== "home" || userActedSince(startedAt)) return;
      if (deleted.has(sessionID) || !api.data.session.get(sessionID)) return;
      if (api.ui.tabs?.enabled?.()) api.ui.tabs.focus(sessionID);
      else api.ui.router.navigate({ type: "session", sessionID });
      return;
    }
  }

  const poll = setInterval(() => {
    const now = Date.now();
    if (now - lastTick > WAKE_GAP_MS) disruptedAt = now;
    lastTick = now;

    const current = route();
    if (current?.type === "session") {
      lastSessionID = current.sessionID;
      lastWasSession = true;
      return;
    }
    if (current?.type !== "home" || !lastWasSession) {
      lastWasSession = false;
      return;
    }
    lastWasSession = false;

    const sessionID = lastSessionID;
    if (!sessionID || restoring || deleted.has(sessionID)) return;
    if (now - disruptedAt > RECOVERY_WINDOW_MS || userActedSince(now)) return;
    restoring = restore(sessionID, now)
      .catch(() => {})
      .finally(() => {
        restoring = undefined;
      });
  }, POLL_MS);
  cleanups.push(() => clearInterval(poll));

  return () => {
    disposed = true;
    for (const cleanup of cleanups.splice(0)) {
      try {
        cleanup();
      } catch {}
    }
  };
}
