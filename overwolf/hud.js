"use strict";

const $ = id => document.getElementById(id);
const svgNS = "http://www.w3.org/2000/svg";
const numeric = value => Number(value) || 0;
function svg(tag, attrs) {
  const node = document.createElementNS(svgNS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  return node;
}
function render(snapshot) {
  const rounds = (snapshot.rounds || []).filter(r => r.final);
  const all = snapshot.rounds || [];
  const damageRounds = rounds.filter(r => r.damage !== null);
  const totalDamage = damageRounds.reduce((sum, r) => sum + numeric(r.damage), 0);
  const totalHits = damageRounds.reduce((sum, r) => sum + numeric(r.hits), 0);
  const totalHeadshots = damageRounds.reduce((sum, r) => sum + numeric(r.headshots), 0);
  $("source").textContent = snapshot.source || "WAITING FOR GAME DATA";
  $("map").textContent = snapshot.map || "LIVE MATCH";
  $("player").textContent = snapshot.player || "YOU";
  $("round").textContent = snapshot.round ? String(snapshot.round).padStart(2, "0") : "--";
  $("score").textContent = `${numeric(snapshot.score?.won)} : ${numeric(snapshot.score?.lost)}`;
  $("kda").textContent = ["kills", "deaths", "assists"].map(k => numeric(snapshot.totals?.[k])).join(" / ");
  $("adr").textContent = damageRounds.length ? String(Math.round(totalDamage / damageRounds.length)) : "--";
  $("agent").textContent = `AGENT ${snapshot.agent || "--"}`;
  $("headshots").textContent = totalHits ? `HS ${Math.round(100 * totalHeadshots / totalHits)}%` : "HS --";
  $("rank").textContent = `RANK ${snapshot.rank || "--"}`;
  $("graph-end").textContent = rounds.length ? `ROUND ${String(rounds[rounds.length - 1].number).padStart(2, "0")}` : "AWAITING DATA";

  const graph = $("damage-graph");
  graph.replaceChildren();
  for (const y of [30, 75, 120, 155]) graph.append(svg("line", {x1: 0, y1: y, x2: 570, y2: y,
    stroke: "#9eeffc26", "stroke-width": 1, "stroke-dasharray": "4 7"}));
  const shown = rounds.slice(-26);
  const max = Math.max(200, ...shown.map(r => numeric(r.damage)));
  if (shown.length) {
    const step = 558 / shown.length;
    shown.forEach((round, index) => {
      const x = 8 + index * step + step * .17;
      const h = Math.max(2, 130 * numeric(round.damage) / max);
      const bar = svg("rect", {x, y: 154 - h, width: Math.max(4, step * .62), height: h,
        rx: 2, fill: round.won === false ? "#ff8699" : "#8ff5ff", opacity: .88});
      graph.append(bar);
      if (shown.length <= 16) {
        const number = svg("text", {x: x + step * .3, y: 166, "text-anchor": "middle",
          fill: "#83abbc", "font-size": 9});
        number.textContent = String(round.number);
        graph.append(number);
      }
    });
  }
  const strip = $("round-results");
  strip.replaceChildren();
  if (!all.length) {
    const placeholder = document.createElement("span");
    placeholder.className = "placeholder";
    placeholder.textContent = "Round results appear after play begins.";
    strip.append(placeholder);
  } else {
    all.filter(r => r.final).slice(-24).forEach(round => {
      const chip = document.createElement("span");
      chip.className = `chip ${round.won === false ? "loss" : round.won === null ? "unknown" : ""}`;
      chip.textContent = round.won === true ? "W" : round.won === false ? "L" : "·";
      chip.title = `Round ${round.number}: ${round.kills} K / ${round.deaths} D / ${round.assists} A`;
      strip.append(chip);
    });
  }
}

if (typeof overwolf !== "undefined") {
  overwolf.windows.onMessageReceived.addListener(message => {
    if (message.id === "snapshot") render(message.content);
  });
  const controller = overwolf.windows.getMainWindow();
  if (controller && controller.hudState) render(controller.hudState.snapshot());
} else {
  render({source: "DESIGN PREVIEW · NO LIVE GAME", map: "ASCENT", player: "YOU", agent: "CLOVE",
    rank: "GOLD 3", round: 9, score: {won: 5, lost: 3}, totals: {kills: 13, deaths: 8, assists: 5},
    rounds: [120, 235, 90, 310, 165, 280, 65, 190].map((damage, index) => ({number: index + 1,
      damage, kills: index % 3, deaths: index % 2, assists: 1, hits: 4, headshots: 1,
      won: index % 3 !== 1, final: true}))});
}
