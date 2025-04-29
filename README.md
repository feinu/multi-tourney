# Multiplayer Tournament Matchmaker

Pairing players in a multiplayer tournament across multiple rounds is hard.
Some pairings of players inevitably occur more frequently than others.

This script attempts to find a near-optimal solution to a specific tournament structure
used for a group of *Heat: Pedal to the Metal* players on Board Game Arena.

Basic constraints:
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

# Configuration

Configuration is in `config.yml`, where you can set player names, rounds and iterations.
Setting `iterations` to 5000 seems to provide a decent solution, although you should go make a coffee while it runs.

## Disclaimer
* _This is a cobbled-together rubbish script, don't judge me_.
* Use at own risk

## License
```
Copyright 2025 Duane Churms

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```
