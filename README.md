# Multiplayer Tournament Matchmaker
Pairing players in a multiplayer tournament across multiple rounds is hard.
Some pairings of players inevitably occur more frequently than others.

This script attempts to find a near-optimal solution to a specific tournament structure
used for a group of *Heat: Pedal to the Metal* players on Board Game Arena.
This includes:
* Multiple rounds at different tracks
* Teams, and team mates do not face each other
* Some rounds have fewer participants to allow rest weeks
* Potentially an initial round that's been pre-populated
* Rankings within each team (not that important)

Analytical methods to solve the n-way stable marriage problem failed, so this uses a Monte Carlo simulation.
For each round, players get randomly assigned to matches, and a heuristic gets calculated for optimality of the assignments.
After a given number of iterations has been run, the best assignments are kept and the next round is generated.

The heuristic used tries to primarily minimise the difference between all players most-frequent and least-frequent opponents.
This is referred to as the player's imbalance.
As a tie breaker, the heuristic also tries to have as few players as possible with a high imbalance.

Configuration is in `config.yml`, where you can set player names, rounds and iterations.
Setting `iterations` to 5000 seems to provide a decent solution, although you should go make a coffee while it runs.
