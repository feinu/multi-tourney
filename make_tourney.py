#!/usr/bin/env python3
import random
import statistics
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    ForeignKey,
    Table,
    select,
    text
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship,
)
import yaml

Base = declarative_base()


match_participants = Table(
    "match_participants",
    Base.metadata,
    Column("match_id", ForeignKey("match.id"), primary_key=True),
    Column("player_name", ForeignKey("player.name"), primary_key=True),
)


class Player(Base):
    __tablename__ = "player"
    name = Column(String, primary_key=True)
    rank = Column(Integer)
    team_name = Column(String, ForeignKey("team.name"))
    team = relationship("Team", back_populates="players")
    matches = relationship(
        "Match", secondary=match_participants, back_populates="participants"
    )

    def __repr__(self):
        return f"{self.name}[{self.team} {self.rank}]"

    def pretty(self):
        return f"{repr(self):<22}"

    def meetings(self):
        query = f"""SELECT player_name, count(*) FROM match_participants
        WHERE player_name != '{self.name}' AND match_id in (
            SELECT match_id FROM match_participants
            WHERE player_name = '{self.name}'
        )
        GROUP BY player_name"""
        results = session.execute(text(query)).all()
        counts = {
            p[0].name: 0
            for p in session.execute(select(Player).where(Player.team != self.team))
            if p[0].name not in [r[0] for r in results]
        }
        for name, count in results:
            counts[name] = count
        return counts

    def min_meetings(self):
        return min(self.meetings().values())

    def players_at_min_meetings(self, verbose=False):
        meetings = self.meetings()
        min_meetings = min(self.meetings().values())
        players = [
            session.query(Player).filter(Player.name == k).first()
            for k, v in meetings.items()
            if v == min_meetings
        ]
        if False and verbose:
            print(f"{self} needs to play {players}")
        return players

    def weariness(self, opponents):
        """
        Return a score for how tired player is of facing opponents
        return sum(
            len(set(self.matches).intersection(opponent.matches))
            for opponent in opponents
        )
        """
        if not opponents:
            return 0
        return max(
            len(set(self.matches).intersection(opponent.matches))
            for opponent in opponents
        )

    def imbalance(self, meetings=None):
        if not meetings:
            meetings = self.meetings()
        return max(meetings.values()) - min(meetings.values())

    def variance(self, meetings=None):
        if not meetings:
            meetings = self.meetings()
        return statistics.pvariance(meetings.values())

    def projected_imbalance(self, opponents):
        meetings = self.meetings()
        for p in opponents:
            meetings[p.name] += 1
        return self.imbalance(meetings)

    def projected_variance(self, opponents):
        meetings = self.meetings()
        for p in opponents:
            meetings[p.name] += 1
        return self.variance(meetings)

    def raises_floor(self, opponents):
        meetings = self.meetings()
        floor_opponents = [
            k for k, v in meetings.items() if v == min(meetings.values())
        ]
        return len(floor_opponents)

    def raises_ceiling(self, opponents):
        meetings = self.meetings()
        ceil_opponents = [
            k for k, v in meetings.items() if v == max(meetings.values())
        ]
        return len(ceil_opponents)

    def benefit(self, opponents):
        return - sum(
            [
                self.raises_floor(opponents),
                sum(p.raises_floor(self) for p in opponents),
                - self.raises_ceiling(opponents),
                - sum(p.raises_ceiling(self) for p in opponents),
            ]
        )


class Team(Base):
    __tablename__ = "team"
    name = Column(String, primary_key=True)
    players = relationship("Player", order_by=Player.rank, back_populates="team")

    def from_config(self, team, teamconfig):
        self.name = team
        self.player = [
            Player(team, name, rank)
            for name, rank in teamconfig.items()
        ]

    def __str__(self):
        return self.name


class Match(Base):
    __tablename__ = "match"
    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, ForeignKey("round.id"))
    round = relationship("Round", back_populates="matches")
    participants = relationship(
        "Player",
        order_by=Player.team_name,
        secondary=match_participants,
        back_populates="matches",
    )

    def __repr__(self):
        return f"M{self.id}(" + ",".join(p.name[:4] for p in self.participants) + ")"

    def add_participant(self, player):
        if player.team in [p.team for p in self.participants]:
            raise ValueError("Player/team already in match")
        self.participants.append(player)
        session.commit()

    def pretty(self):
        return ", ".join([p.pretty() for p in self.participants])

    def has_team(self, team):
        return team in [p.team for p in self.participants]


class Round(Base):
    __tablename__ = "round"
    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(Integer)
    track = Column(String)
    tournament_id = Column(Integer, ForeignKey("tournament.id"))
    tournament = relationship("Tournament", back_populates="rounds")
    matches = relationship("Match", order_by=Match.id, back_populates="round")

    def pretty(self):
        return "\n".join(
            [
                f"--- Round {self.number}: {self.track} ---",
                *["  " + m.pretty() for m in self.matches],
            ]
        )

    def unmatched_players(self):
        unmatched = [
            p[0] for p in session.execute(select(Player)).all()
            if not set(self.matches).intersection(p[0].matches)
        ]
        return unmatched

    def allocate_player_to_match(self, player):
        """
        Allocate a player to their optimal match based on weariness
        """
        match_preference = sorted(
            [
                (
                    match,
                    (
                        player.projected_imbalance(match.participants) +
                        # player.projected_variance(match.participants) + 
                        player.raises_ceiling(match.participants) / 2
                    ) / max(1, len(match.participants))
                )
                for match in self.matches
                if not match.has_team(player.team)
            ],
            key=lambda x: x[1],
        )
        # print(f"{player}: {match_preference}")
        match_preference[0][0].add_participant(player)


class Tournament(Base):
    __tablename__ = "tournament"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    rounds = relationship("Round", order_by=Round.number, back_populates="tournament")

    def pretty(self):
        length = len(self.name)
        return "\n".join(
            [
                "=" * (length + 4),
                f"# {self.name} #",
                "=" * (length + 4),
                *[r.pretty() for r in self.rounds],
            ]
        )

    def generate_rests(self):
        """
        Rotate through the teams, resting a random player from each team.
        This means that "adjacent" teams will end up getting rested on
        the same week, and opposite teams will rarely be rested at the same time.
        Don't think this matters
        """
        teams = [
            t[0] for t in session.execute(select(Team)).all()
        ]
        for team in teams:
            team.rest_sequence = [1, 2, 3, 4]
            random.shuffle(team.rest_sequence)
        random.shuffle(teams)

        self.unrested = []
        for i in range(4):
            for team in teams:
                self.unrested.append(
                    session.scalar(
                        select(Player)
                        .where(Player.team == team)
                        .where(Player.rank == team.rest_sequence[i])
                    )
                )

    def make_round_random(self, iterations=1):
        round_num = len(self.rounds)
        track = rounds_input[round_num]["track"]
        resting = rounds_input[round_num]["players"] < 7
        print(f"--------- STARTING NEW ROUND, RESTING = {resting} ---------")
        print(f"unrested: {len(self.unrested)}")
        attempts = 0
        min_score = 9999
        start_stat = stat()
        end_stat = start_stat * 100
        rested = []
        if resting:
            rested = self.unrested[-4:]
            self.unrested = self.unrested[:-4]
        for attempts in range(iterations):
            r = Round(
                tournament=self,
                number=round_num + 1,
                track=track,
            )
            session.add(r)
            matches = []
            for i in range(4):
                m = Match(round=r)
                m.has_rested = False
                session.add(m)
                matches.append(m)
            teams = [t[0] for t in session.execute(select(Team)).all()]
            random.shuffle(teams)
            for team in teams:
                players = [p for p in team.players]
                random.shuffle(players)
                for i in range(4):
                    # Assign to a match that has the fewest participants
                    next_match = [
                        m for m in matches
                        if len(m.participants) == min(
                            map(lambda x: len(x.participants), matches)
                        )
                    ][0]
                    if players[i] not in rested:
                        next_match.add_participant(players[i])
            end_stat = stat()
            if end_stat < min_score:  # or attempts > 1000:
                min_score = end_stat
                print(f"Improved to {end_stat}")
                best_matches = [
                    m.participants
                    for m in matches
                ]

            for m in matches:
                session.delete(m)
            session.delete(r)
            session.commit()

        r = Round(
            tournament=self,
            number=round_num + 1,
            track=track,
        )
        session.add(r)
        for players in best_matches:
            m = Match(round=r)
            for p in players:
                m.add_participant(p)
            session.add(m)
        session.commit()

    def make_round(self, players_per_race: int = 7, rested: list = []):
        """
        Attempt at an actual algorithm.
        It doesn't work well at all.
        """
        def key(p):
            return p.min_meetings() + 0.1 / len(p.players_at_min_meetings()),

        print("--------- STARTING NEW ROUND ---------")
        print(statistics.pvariance([x[0] for x in imbalance_data()], mu=0))
        r = Round(tournament=self)
        session.add(r)

        unmatched_players = sorted(r.unmatched_players(), key=key, reverse=True)
        # Pre-populate matches with low-meetup pairings
        for n in range(4):
            m = Match(round=r)
            session.add(m)
            player = unmatched_players.pop()
            opponents = player.players_at_min_meetings(verbose=True)
            random.shuffle(opponents)
            # found = False
            opponents = [o for o in opponents if o in unmatched_players]
            """
            for opponent in opponents:
                if opponent in unmatched_players:
                    found = True
                    break
            """

            if False:
                print(
                    f"Pre-populating {player}({key(player)})"
                )
            m.add_participant(player)
            for o in opponents:
                if o.raises_ceiling(m.participants) < 2:
                    try:
                        m.add_participant(o)
                        unmatched_players.remove(o)
                    except ValueError as e:
                        print(e)
            print(m.pretty())
            session.commit()
            unmatched_players.sort(key=key, reverse=True)

        while unmatched_players:
            # Work on the player with the biggest imbalance first
            player = unmatched_players.pop()
            if player in rested:
                continue
            r.allocate_player_to_match(player)
            session.commit()


def preseed_players(teams_config):
    for team, players in teams_config.items():
        t = Team(name=team)
        session.add(t)
        session.commit()
        for p, rank in players.items():
            session.add(Player(name=p, rank=rank, team=t))
    session.commit()


def preseed_races(t: Tournament, race_config: dict):
    for roundname, races in race_config.items():
        rnd = Round(tournament=t, number=1, track="Mexico")
        session.add(rnd)
        for race, participants in races.items():
            match = Match(round=rnd)
            session.add(match)
            for p in participants:
                try:
                    player = session.query(Player).filter(Player.name == p).one()
                except Exception:
                    print(f"While looking for {p}:")
                    raise
                match.add_participant(player)
    session.commit()


def imbalance_data():
    return sorted(
        [(p.imbalance(), p) for p in session.query(Player).all()],
        key=lambda x: x[0],
        reverse=True
    )


def imbalance_summary(full=False):
    imbalances = imbalance_data()
    minimum = min(i[0] for i in imbalances)
    maximum = max(i[0] for i in imbalances)
    for p in imbalances:
        if full or p[0] in (minimum, maximum):
            print(p[0], p[1])


def stat():
    """
    Most important is maximum imbalance for any player
    Of secondary importance is keeping few players at high imbalances,
    hence using variance with respect to zero
    """
    return (
        max(p[0] for p in imbalance_data()) +
        statistics.pvariance([x[0] for x in imbalance_data()], mu=0) / 100
    )


with open("config.yml", "r") as f:
    config_input = yaml.safe_load(f)
    team_input = config_input["teams"]
    races_input = config_input["races"]
    rounds_input = config_input["rounds"]
    iterations = config_input["iterations"]

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

preseed_players(team_input)

tourney = Tournament(name="Winter Champs")
preseed_races(tourney, races_input)

t = session.query(Tournament).first()
t.generate_rests()
for i in range(11):
    t.make_round_random(iterations=iterations)
imbalance_summary()
print(statistics.pvariance([x[0] for x in imbalance_data()], mu=0))
