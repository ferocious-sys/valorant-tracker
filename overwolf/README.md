# Tactical HUD (Overwolf prototype)

This is the live, Tab-held in-game companion to the Python tracker. It uses [Overwolf's VALORANT game events](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/valorant/) for **your own** scoreboard, round damage reports, score, map, agent, and visible rank. Holding Tab shows a click-through HUD at the top left; releasing Tab hides it. The hotkey passes through to VALORANT, so the normal scoreboard still opens.

The HUD displays K/D/A, damage per completed round, average damage, headshot rate from reported hits, round wins/losses, and a personal damage graph. Data arrives when Overwolf emits events. A round's final K/D/A is calculated from cumulative scoreboard differences; it may remain incomplete until the next round's update. Missing events are shown as unknown, not invented. It stores no match history and never requests enemy stats.

## Try the design

Open `hud.html` in a browser. Outside Overwolf it shows a clearly marked **DESIGN PREVIEW** with sample values. Run `node --test model.test.js` to test the event model.

## Run in VALORANT

Overwolf must approve and whitelist the developer account before it can load an unpacked extension or install an unsigned package. After approval, open Overwolf **Settings → About → Development options → Load unpacked extension**, and select this `overwolf` folder. Start VALORANT with Overwolf's game overlay enabled. The desktop controller reports whether the event feed connected; hold Tab in a match to show the HUD. If Tab conflicts with another app, change this app's hotkey in Overwolf settings.

This prototype has passed local model tests and [manifest schema validation](https://dev.overwolf.com/ow-native/reference/manifest/validate-your-manifest-json/). It has not been tested inside a running VALORANT match or released as a signed Overwolf app. It is separate from `!overlay`, the existing F8 desktop rank card. The Python one-command installer does not install this Overwolf prototype.

Riot's [VALORANT developer policy](https://developer.riotgames.com/docs/valorant) disallows opponent scouting and live overlays that immediately direct play. The HUD limits itself to a player's own performance and gives no tactical recommendations.
