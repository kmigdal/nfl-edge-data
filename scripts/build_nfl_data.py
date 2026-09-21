import json
import os
import shutil
from datetime import datetime, timezone

import pandas as pd

SEASON = 2026
RECENT_GAMES = 6

PLAYER_URL = (
    f"https://github.com/nflverse/nflverse-data/"
    f"releases/download/stats_player/stats_player_week_{SEASON}.csv"
)

TEAM_URL = (
    f"https://github.com/nflverse/nflverse-data/"
    f"releases/download/stats_team/stats_team_week_{SEASON}.csv"
)

OUTPUT_DIR = "data"


TEAM_STATS = [
    "completions",
    "attempts",
    "passing_yards",
    "passing_tds",
    "passing_interceptions",
    "sacks_suffered",
    "passing_air_yards",
    "passing_yards_after_catch",
    "passing_first_downs",
    "passing_epa",
    "passing_cpoe",
    "carries",
    "rushing_yards",
    "rushing_tds",
    "rushing_first_downs",
    "rushing_epa",
    "targets",
    "receptions",
    "receiving_yards",
    "receiving_tds",
    "receiving_air_yards",
    "receiving_yards_after_catch",
    "receiving_first_downs",
    "receiving_epa",
    "def_tackles_solo",
    "def_tackle_assists",
    "def_tackles_for_loss",
    "def_sacks",
    "def_qb_hits",
    "def_interceptions",
    "def_pass_defended",
    "fg_made",
    "fg_att",
    "pt_att",
    "pt_yards",
    "pt_inside_20",
    "pt_touchback",
    "pt_return_yards",
    "pt_net_yards",
]


PLAYER_STATS = [
    "completions",
    "attempts",
    "passing_yards",
    "passing_tds",
    "passing_interceptions",
    "sacks_suffered",
    "passing_air_yards",
    "passing_yards_after_catch",
    "passing_first_downs",
    "passing_epa",
    "passing_cpoe",
    "carries",
    "rushing_yards",
    "rushing_tds",
    "rushing_first_downs",
    "rushing_epa",
    "targets",
    "receptions",
    "receiving_yards",
    "receiving_tds",
    "receiving_air_yards",
    "receiving_yards_after_catch",
    "receiving_first_downs",
    "receiving_epa",
    "target_share",
    "special_teams_tds",
    "def_tackles_solo",
    "def_tackles_with_assist",
    "def_tackle_assists",
    "def_tackles_for_loss",
    "def_sacks",
    "def_sack_yards",
    "def_qb_hits",
    "def_interceptions",
    "def_pass_defended",
    "def_tds",
]


def normal_value(value):
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    return value


def compact_record(row, fields, skip_zero=False):
    result = {}

    for field in fields:
        if field not in row.index:
            continue

        value = normal_value(row[field])

        if value is None:
            continue

        if skip_zero and isinstance(value, (int, float)) and value == 0:
            continue

        result[field] = value

    return result


def main():
    print("Downloading current nflverse player statistics...")
    players = pd.read_csv(PLAYER_URL)

    print("Downloading current nflverse team statistics...")
    teams = pd.read_csv(TEAM_URL)

    if "season" in players.columns:
        players = players[players["season"] == SEASON]

    if "season" in teams.columns:
        teams = teams[teams["season"] == SEASON]

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    team_codes = sorted(
        set(players["team"].dropna().unique())
        | set(teams["team"].dropna().unique())
    )

    generated = datetime.now(timezone.utc).isoformat()

    player_stats_available = [
        stat for stat in PLAYER_STATS if stat in players.columns
    ]

    team_stats_available = [
        stat for stat in TEAM_STATS if stat in teams.columns
    ]

    for team in team_codes:
        print(f"Building compact data for {team}...")

        team_rows = teams[teams["team"] == team].copy()

        if "week" in team_rows.columns:
            team_rows = team_rows.sort_values("week")

        recent_team = team_rows.tail(RECENT_GAMES)

        team_recent = []

        for _, row in recent_team.iterrows():
            record = compact_record(
                row,
                ["week", "game_id", "opponent_team"] + team_stats_available
            )
            team_recent.append(record)

        team_season_average = {}

        if not team_rows.empty:
            for stat in team_stats_available:
                if pd.api.types.is_numeric_dtype(team_rows[stat]):
                    value = team_rows[stat].mean()

                    if not pd.isna(value):
                        team_season_average[stat] = round(float(value), 3)

        team_players = players[players["team"] == team].copy()

        relevant_mask = pd.Series(False, index=team_players.index)

        for stat in player_stats_available:
            if pd.api.types.is_numeric_dtype(team_players[stat]):
                relevant_mask = relevant_mask | (
                    team_players[stat].fillna(0) != 0
                )

        team_players = team_players[relevant_mask]

        player_payload = []

        if not team_players.empty:
            for player_id, player_rows in team_players.groupby("player_id"):
                player_rows = player_rows.sort_values("week")

                latest = player_rows.iloc[-1]

                player = {
                    "player_id": normal_value(player_id),
                    "player_name": normal_value(
                        latest.get("player_name")
                    ),
                    "player_display_name": normal_value(
                        latest.get("player_display_name")
                    ),
                    "position": normal_value(
                        latest.get("position")
                    ),
                    "position_group": normal_value(
                        latest.get("position_group")
                    ),
                    "games": int(len(player_rows)),
                }

                season_totals = {}

                for stat in player_stats_available:
                    if pd.api.types.is_numeric_dtype(player_rows[stat]):
                        value = player_rows[stat].sum()

                        if value != 0 and not pd.isna(value):
                            season_totals[stat] = round(float(value), 3)

                player["season_totals"] = season_totals

                recent = []

                for _, row in player_rows.tail(RECENT_GAMES).iterrows():
                    game = compact_record(
                        row,
                        [
                            "week",
                            "game_id",
                            "opponent_team",
                        ] + player_stats_available,
                        skip_zero=True,
                    )

                    recent.append(game)

                player["recent"] = recent
                player_payload.append(player)

        payload = {
            "season": SEASON,
            "team": team,
            "generated_utc": generated,
            "team_games_played": int(len(team_rows)),
            "team_season_average": team_season_average,
            "team_recent": team_recent,
            "players": player_payload,
        }

        output_file = os.path.join(
            OUTPUT_DIR,
            f"{team}.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                payload,
                f,
                ensure_ascii=False,
                separators=(",", ":"),
            )

    index = {
        "season": SEASON,
        "generated_utc": generated,
        "teams": team_codes,
        "recent_games_included": RECENT_GAMES,
        "files": {
            team: f"{team}.json"
            for team in team_codes
        },
    }

    with open(
        os.path.join(OUTPUT_DIR, "index.json"),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            index,
            f,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    print("Compact NFL Edge data build complete.")


if __name__ == "__main__":
    main()
