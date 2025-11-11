"""Application settings configuration"""
from dataclasses import dataclass, field
from typing import List, Set, Dict


@dataclass
class DirectorySettings:
    """Directory configuration"""
    staging: str = ""
    tv_shows: str = ""
    movies: str = ""
    anime: str = ""
    trash: str = ""


@dataclass
class CleanupSettings:
    """Cleanup tool configuration"""
    selected: Set[str] = field(default_factory=lambda: {
        ".jpg", ".jpeg", ".png", ".gif", ".txt", ".nfo", ".srt"
    })
    custom_exts_str: str = ""


@dataclass
class Settings:
    """Application settings"""

    # Directories
    directories: DirectorySettings = field(default_factory=DirectorySettings)

    # Naming patterns
    series_pattern: str = "{clean}"
    episode_pattern: str = "{series} - S{season:02d}E{episode:02d}{ext}"
    movie_pattern: str = "{series}{ext}"

    # UI preferences
    console_visible: bool = True
    show_organize_confirmation: bool = True  # Show confirmation dialog after organizing

    # Organize preferences
    use_season_00_for_specials: bool = False  # False = "Specials", True = "Season 00"
    org_folder_anime: str = "Anime"  # Organizational folder name for anime
    org_folder_tv_shows: str = "TV Shows"  # Organizational folder name for TV shows
    org_folder_movies: str = "Movies"  # Organizational folder name for movies

    # Hotkeys configuration
    hotkeys: Dict[str, str] = field(default_factory=lambda: {
        # Season assignment (1-10)
        "season_1": "1",
        "season_2": "2",
        "season_3": "3",
        "season_4": "4",
        "season_5": "5",
        "season_6": "6",
        "season_7": "7",
        "season_8": "8",
        "season_9": "9",
        "season_10": "0",
        # Season assignment (11-20)
        "season_11": "Ctrl+1",
        "season_12": "Ctrl+2",
        "season_13": "Ctrl+3",
        "season_14": "Ctrl+4",
        "season_15": "Ctrl+5",
        "season_16": "Ctrl+6",
        "season_17": "Ctrl+7",
        "season_18": "Ctrl+8",
        "season_19": "Ctrl+9",
        "season_20": "Ctrl+0",
        # Quick actions (organize dialog)
        "move_to_specials": "S",
        "move_to_movies": "M",
        "rename_selected": "F2",
        "delete_selected": "Delete",
        "undo": "Ctrl+Z",
        "redo": "Ctrl+Y",
        "select_all": "Ctrl+A",
        "execute": "Ctrl+Return",
        # Media tree actions (main window)
        "open_anime_dialog": "A",
        "open_movie_dialog": "M",
        "open_tv_dialog": "T",
    })

    # Move presets for quick access
    move_presets: List[str] = field(default_factory=list)

    # Cleanup configuration
    cleanup_ext_states: Dict[str, any] = field(default_factory=lambda: {
        "selected": [".jpg", ".jpeg", ".png", ".gif", ".txt", ".nfo", ".srt"],
        "custom_exts_str": ""
    })

    # Fluff patterns for name cleaning
    fluff_patterns: List[str] = field(default_factory=lambda: [
        r"\[.*?\]",
        r"\(.*?\)",
        r"\b(1080p|720p|2160p|4k|x264|x265|h264|h265|hevc|webrip|bluray|bdrip)\b",
        r"(s\d+)",
    ])

    def to_dict(self) -> dict:
        """Convert settings to dictionary for JSON serialization"""
        return {
            "directories": {
                "staging": self.directories.staging,
                "tv_shows": self.directories.tv_shows,
                "movies": self.directories.movies,
                "anime": self.directories.anime,
                "trash": self.directories.trash,
            },
            "series_pattern": self.series_pattern,
            "episode_pattern": self.episode_pattern,
            "movie_pattern": self.movie_pattern,
            "console_visible": self.console_visible,
            "show_organize_confirmation": self.show_organize_confirmation,
            "use_season_00_for_specials": self.use_season_00_for_specials,
            "org_folder_anime": self.org_folder_anime,
            "org_folder_tv_shows": self.org_folder_tv_shows,
            "org_folder_movies": self.org_folder_movies,
            "hotkeys": self.hotkeys,
            "move_presets": self.move_presets,
            "cleanup_ext_states": self.cleanup_ext_states,
            "fluff_patterns": self.fluff_patterns,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create Settings from dictionary"""
        # Extract directories
        dirs_data = data.get("directories", {})
        directories = DirectorySettings(
            staging=dirs_data.get("staging", ""),
            tv_shows=dirs_data.get("tv_shows", ""),
            movies=dirs_data.get("movies", ""),
            anime=dirs_data.get("anime", ""),
            trash=dirs_data.get("trash", "")
        )

        return cls(
            directories=directories,
            series_pattern=data.get("series_pattern", "{clean}"),
            episode_pattern=data.get("episode_pattern", "{series} - S{season:02d}E{episode:02d}{ext}"),
            movie_pattern=data.get("movie_pattern", "{series}{ext}"),
            console_visible=data.get("console_visible", True),
            show_organize_confirmation=data.get("show_organize_confirmation", True),
            use_season_00_for_specials=data.get("use_season_00_for_specials", False),
            org_folder_anime=data.get("org_folder_anime", "Anime"),
            org_folder_tv_shows=data.get("org_folder_tv_shows", "TV Shows"),
            org_folder_movies=data.get("org_folder_movies", "Movies"),
            hotkeys=data.get("hotkeys", {}),
            move_presets=data.get("move_presets", []),
            cleanup_ext_states=data.get("cleanup_ext_states", {
                "selected": [".jpg", ".jpeg", ".png", ".gif", ".txt", ".nfo", ".srt"],
                "custom_exts_str": ""
            }),
            fluff_patterns=data.get("fluff_patterns", [])
        )
