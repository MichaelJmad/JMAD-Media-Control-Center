import os
import random
import string

# === SETTINGS ===
BASE_DIR = "DummyMedia"
NUM_SERIES = 5        # Number of different shows
MAX_SEASONS = 3       # Max seasons per show
MAX_EPISODES = 12      # Max episodes per season

# Characters for random complex parts
CHARS = string.ascii_letters + string.digits + " []().-_"

# Some base series names
BASE_SERIES_NAMES = [
    "Blue Exorcist", "Attack on Titan", "My Hero Academia",
    "Demon Slayer", "One Piece", "Pokemon", "Naruto"
]

def random_suffix():
    """Generate a random messy suffix like [BD][1080p]..."""
    parts = [
        "[BD]", "[1080p]", "[720p]", "[Dual Audio]",
        "[HEVC 10bit x265]", "[Tenrai-Sensei]",
        "[Season]", "[Specials]", "[Remastered]",
        "[v2]", "[Batch]"
    ]
    return "".join(random.sample(parts, random.randint(2, 5)))

def create_dummy_files():
    os.makedirs(BASE_DIR, exist_ok=True)

    for _ in range(NUM_SERIES):
        base_name = random.choice(BASE_SERIES_NAMES)

        num_seasons = random.randint(1, MAX_SEASONS)
        for season in range(1, num_seasons + 1):
            # Create messy folder name for this season
            season_folder_name = (
                f"{base_name} {random_suffix()} [Season {season}]"
                if random.choice([True, False]) else
                f"{base_name} {random_suffix()} s{season}"
            )

            series_path = os.path.join(BASE_DIR, season_folder_name)
            os.makedirs(series_path, exist_ok=True)

            # Decide episode style for this season
            style = random.choice(["sxxexx", "flatnum", "rootflat"])

            num_eps = random.randint(2, MAX_EPISODES)
            for ep in range(1, num_eps + 1):
                if style == "sxxexx":
                    ep_name = f"s{season:02d}e{ep:02d}.mkv"
                    ep_path = os.path.join(series_path, ep_name)

                elif style == "flatnum":
                    ep_name = f"{base_name} {ep:03d}.mkv"
                    ep_path = os.path.join(series_path, ep_name)

                elif style == "rootflat":
                    # Root-style season folder (no subfolder)
                    ep_name = f"{base_name} {ep:03d}.mkv"
                    ep_path = os.path.join(series_path, ep_name)

                with open(ep_path, "w") as f:
                    f.write("DUMMY VIDEO FILE\n")

if __name__ == "__main__":
    create_dummy_files()
    print(f"Dummy media structure created inside '{BASE_DIR}'")
