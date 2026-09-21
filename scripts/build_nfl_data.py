import json
import os
from datetime import datetime, timezone

import pandas as pd

SEASON = 2026

PLAYER_URL = (
    f"https://github.com/nflverse/nflverse-data/"
    f"releases/download/stats_player/stats_player_week_{SEASON}.csv"
)

TEAM_URL = (
    f"https://github.com/nflverse/nflverse-data/"
    f"releases/download/stats_team/stats_team_week_{SEASON}.csv"
)

OUTPUT_DIR = "data"


def clean_records(df):
    records = []

    for row in df.to_dict(orient="records"):
        clean = {}

        for key, value in row.items():
            if pd.isna(value):
                continue

            if hasattr(value, "item"):
                value = value.item()

            clean[key] = value

        records.append(clean)

    return records


def player_columns(df):
    always_keep = {
        "player_id",
        "player_name",
        "player_display_name",
        "position",
        "position_group",
        "season",
        "week",
        "season_type",
        "game_id",
        "team",
        "opponent_team",
        "completions",
        "attempts",
        "carries",
        "targets",
        "receptions",
    }

    keywords = (
        "passing",
        "rushing",
        "receiving",
        "target",
        "reception",
        "carry",
        "sack",
        "tackle",
        "interception",
        "pressure",
        "fumble",
        "punt",
        "kick",
        "field_goal",
        "fantasy",
        "def_",
        "special",
    )

    keep = []

    for col in df.columns:
        name = col.lower()

        if col in always_keep or any(word in name for word in keywords):
            keep.append(col)

    return keep


def main():
    print("Downloading current nflverse player statistics...")
    players = pd.read_csv(PLAYER_URL)

    print("Downloading current nflverse team statistics...")
    teams = pd.read_csv(TEAM_URL)

    if "season" in players.columns:
        players = players[players["season"] == SEASON]

    if "season" in teams.columns:
        teams = teams[teams["season"] == SEASON]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    selected_player_columns = player_columns(players)

    team_codes = set()

    if "team" in players.columns:
        team_codes.update(players["team"].dropna().unique())

    if "team" in teams.columns:
        team_codes.update(teams["team"].dropna().unique())

    team_codes = sorted(team_codes)

    generated = datetime.now(timezone.utc).isoformat()

    for team in team_codes:
        player_rows = players[players["team"] == team].copy()

        if "week" in player_rows.columns:
            player_rows = player_rows.sort_values("week")

        team_rows = teams[teams["team"] == team].copy()

        if "week" in team_rows.columns:
            team_rows = team_rows.sort_values("week")

        payload = {
            "season": SEASON,
            "team": team,
            "generated_utc": generated,
            "sources": {
                "player_stats": PLAYER_URL,
                "team_stats": TEAM_URL,
            },
            "team_weekly": clean_records(team_rows),
            "player_weekly": clean_records(
                player_rows[selected_player_columns]
            ),
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

        print(f"Created {output_file}")

    index = {
        "season": SEASON,
        "generated_utc": generated,
        "teams": team_codes,
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

    print("NFL Edge data build complete.")


if __name__ == "__main__":
    main()
