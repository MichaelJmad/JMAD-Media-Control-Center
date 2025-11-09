"""Application constants"""

# Supported video file extensions
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".wmv", ".flv", ".webm"}

# File extensions for cleanup
CLEANUP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif",  # Images
    ".txt", ".nfo", ".md",  # Text files
    ".srt", ".sub", ".ssa", ".ass",  # Subtitles
    ".mp3", ".aac", ".flac",  # Audio
    ".json", ".xml", ".yml", ".yaml",  # Data files
    ".docx", ".pdf",  # Documents
}

# Settings file location
SETTINGS_FILE = "settings.json"

# Patterns file location (for fluff patterns)
PATTERNS_FILE = "patterns.json"

# Application version
APP_VERSION = "1.0.0"
APP_NAME = "JMAD Media Tool"
