const assert = require("node:assert/strict");
const test = require("node:test");
const {makeHudState} = require("./model.js");

test("tracks only local player's live scoreboard and per-round damage", () => {
  const hud = makeHudState();
  hud.ingest("match_id", "game-1");
  hud.ingest("map", "Ascent");
  hud.ingest("roster_1", JSON.stringify({name: "Other#TAG", local: false, rank: 27}));
  hud.ingest("roster_2", JSON.stringify({name: "Me#TAG", local: true, rank: 14, character: "Clove"}));
  hud.ingest("round_number", "1");
  hud.ingest("scoreboard_1", JSON.stringify({name: "Other#TAG", is_local: false, kills: 9}));
  hud.ingest("scoreboard_2", JSON.stringify({name: "Me#TAG", is_local: true,
    kills: 2, deaths: 1, assists: 1}));
  hud.ingest("round_report", JSON.stringify({damage: 210, hit: 4, headshot: 1, final_headshot: 1}));
  hud.ingest("score", JSON.stringify({won: 1, lost: 0}));
  hud.ingest("round_number", "2");
  const state = hud.snapshot();
  assert.equal(state.player, "Me#TAG");
  assert.equal(state.rank, "Gold 3");
  assert.equal(state.agent, "Clove");
  assert.deepEqual(state.rounds[0], {number: 1, kills: 2, deaths: 1, assists: 1,
    damage: 210, hits: 4, headshots: 2, won: true, final: true});
  assert.equal(JSON.stringify(state).includes("Other#TAG"), false);
});

test("handles late score and resets on a new match", () => {
  const hud = makeHudState();
  hud.ingestEvent({info: {match_info: {round_number: "1", scoreboard_0: JSON.stringify({is_local: true, kills: 1})}}});
  hud.ingest("round_number", "2");
  assert.equal(hud.snapshot().rounds[0].won, null);
  hud.ingest("score", JSON.stringify({won: 0, lost: 1}));
  assert.equal(hud.snapshot().rounds[0].won, false);
  hud.ingest("match_id", "new-match");
  assert.equal(hud.snapshot().rounds.length, 0);
});
