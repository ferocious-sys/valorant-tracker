"use strict";

// The game feed sends cumulative scoreboard values and one report per finished round.
// Derive personal round deltas without retaining or rendering other players' data.
function makeHudState() {
  let state = {
    source: "Waiting for VALORANT game events", matchId: null, round: 0,
    map: "LIVE MATCH", agent: "", player: "YOU", rank: "", score: {won: 0, lost: 0},
    totals: {kills: 0, deaths: 0, assists: 0}, rounds: [],
  };
  let lastFinal = {kills: 0, deaths: 0, assists: 0, won: 0, lost: 0};

  const number = value => Math.max(0, Number(value) || 0);
  const decode = value => {
    if (typeof value !== "string") return value;
    try { return JSON.parse(value); } catch { return value; }
  };
  const copy = () => JSON.parse(JSON.stringify(state));
  function reset(matchId = null) {
    state = {source: "LIVE · Overwolf game events", matchId, round: 0, map: "LIVE MATCH",
      agent: "", player: "YOU", rank: "", score: {won: 0, lost: 0},
      totals: {kills: 0, deaths: 0, assists: 0}, rounds: []};
    lastFinal = {kills: 0, deaths: 0, assists: 0, won: 0, lost: 0};
  }
  function roundRecord(round) {
    let record = state.rounds.find(item => item.number === round);
    if (!record) {
      record = {number: round, kills: 0, deaths: 0, assists: 0,
        damage: null, hits: null, headshots: null, won: null, final: false};
      state.rounds.push(record);
      state.rounds.sort((a, b) => a.number - b.number);
    }
    return record;
  }
  function finishRound(round) {
    if (!round || roundRecord(round).final) return;
    const item = roundRecord(round);
    for (const key of ["kills", "deaths", "assists"]) {
      item[key] = Math.max(0, state.totals[key] - lastFinal[key]);
      lastFinal[key] = state.totals[key];
    }
    const won = state.score.won - lastFinal.won;
    const lost = state.score.lost - lastFinal.lost;
    item.won = won > lost ? true : lost > won ? false : null;
    lastFinal.won = state.score.won;
    lastFinal.lost = state.score.lost;
    item.final = true;
  }
  function ingest(key, raw) {
    const value = decode(raw);
    if (/^scoreboard_\d+$/.test(key)) key = "scoreboard";
    if (/^roster_\d+$/.test(key)) key = "roster";
    if (key === "match_id" || key === "pseudo_match_id") {
      if (value && state.matchId !== value) reset(String(value));
    } else if (key === "round_number") {
      const next = number(value);
      if (next && next < state.round) reset(state.matchId);
      if (next > state.round) finishRound(state.round);
      state.round = next;
      if (next) roundRecord(next);
    } else if (key === "score") {
      if (value && typeof value === "object") {
        state.score = {won: number(value.won), lost: number(value.lost)};
        // The score may arrive just after the new round number. Fill the last result then.
        const previous = state.rounds.find(r => r.number === state.round - 1);
        if (previous && previous.won === null) {
          if (state.score.won > lastFinal.won) previous.won = true;
          if (state.score.lost > lastFinal.lost) previous.won = false;
          if (previous.won !== null) {
            lastFinal.won = state.score.won;
            lastFinal.lost = state.score.lost;
          }
        }
      }
    } else if (key === "scoreboard") {
      if (value && typeof value === "object" && value.is_local === true) {
        state.totals = {kills: number(value.kills), deaths: number(value.deaths),
          assists: number(value.assists)};
        if (value.name) state.player = String(value.name).slice(0, 40);
        if (value.character) state.agent = String(value.character).slice(0, 30);
      }
    } else if (key === "roster") {
      if (value && typeof value === "object" && value.local === true) {
        if (value.name) state.player = String(value.name).slice(0, 40);
        if (value.character) state.agent = String(value.character).slice(0, 30);
        const ranks = ["", "", "", "Iron 1", "Iron 2", "Iron 3", "Bronze 1", "Bronze 2", "Bronze 3",
          "Silver 1", "Silver 2", "Silver 3", "Gold 1", "Gold 2", "Gold 3", "Platinum 1", "Platinum 2",
          "Platinum 3", "Diamond 1", "Diamond 2", "Diamond 3", "Ascendant 1", "Ascendant 2",
          "Ascendant 3", "Immortal 1", "Immortal 2", "Immortal 3", "Radiant"];
        state.rank = ranks[number(value.rank)] || "Unranked";
      }
    } else if (key === "round_report") {
      if (state.round && value && typeof value === "object") {
        const item = roundRecord(state.round);
        item.damage = number(value.damage);
        item.hits = number(value.hit);
        item.headshots = number(value.headshot) + number(value.final_headshot);
      }
    } else if (key === "map") {
      if (value) state.map = String(value).slice(0, 40);
    } else if (key === "player_name") {
      if (value) state.player = String(value).slice(0, 40);
    } else if (key === "agent") {
      if (value) state.agent = String(value).slice(0, 30);
    } else if (key === "round_phase" && value === "game_end") {
      finishRound(state.round);
    }
    return copy();
  }
  function ingestEvent(event) {
    const info = event && event.info || {};
    for (const [key, value] of Object.entries(info.match_info || {})) ingest(key, value);
    for (const [key, value] of Object.entries(info.me || {})) ingest(key, value);
    return copy();
  }
  return {ingest, ingestEvent, snapshot: copy, reset};
}

if (typeof module !== "undefined") module.exports = {makeHudState};
