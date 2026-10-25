# Overwolf app idea draft

**Status:** Draft for developer review. This has not been submitted or approved.

## App

**Working name:** Valorant Tracker Tactical HUD  
**Framework:** Overwolf Native web app  
**Game:** VALORANT (game ID 21640)  
**Source and prototype:** https://github.com/ferocious-sys/valorant-tracker/tree/main/overwolf

## Player experience

The player opens a desktop controller and enables the game overlay. During a match, holding Tab shows a transparent, click-through panel alongside the normal scoreboard. The panel summarizes only the local player's performance: K/D/A, damage from completed rounds, average damage, headshot rate from reported hits, round outcomes, and a damage-per-round graph. Releasing Tab hides the panel. The panel does not show opponents' profiles or hidden players, make tactical recommendations, or automate gameplay.

The prototype reads the local player's data from Overwolf's VALORANT Game Events Provider. It keeps live round data in memory and does not upload it. The public app would need a clear opt-in flow and privacy notice before displaying or sharing any player-linked data. If account-linked or historical statistics are added, they would require a Riot-approved production integration and Riot Sign On before public release.

## Distribution and monetization

**Decision needed from project owner:** Overwolf reviews public Appstore apps and requires an Overwolf monetization plan. Choose Overwolf ads in the desktop controller or Tebex subscriptions with free core features. No ads or purchase prompts are planned inside the in-game HUD. The current prototype has neither integration.

## Review readiness

- Prototype source, user flow, and mock data preview are available in the repository.
- The app has a visible desktop controller and a Tab-held in-game window.
- Manifest schema and local event-model tests passed.
- Live VALORANT behavior, hotkey pass-through, and GEP data still need in-game testing after whitelisting.
- Overwolf app idea whitelisting and Riot product approval are separate reviews; neither has been obtained.

## Submission

The project owner must sign in to the [Overwolf app idea form](https://dev.overwolf.com/app-idea-form/) with their Overwolf account. Copy the sections above into the form after settling the public distribution and monetization choice. Describe the live HUD as an experimental prototype, not a released app. Overwolf decides whether to whitelist the app idea.
