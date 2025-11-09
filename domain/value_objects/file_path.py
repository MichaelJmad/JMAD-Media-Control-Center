"""File path value object"""
from pathlib import Path
from typing import Optional


class FilePath:
    """Value object representing a file system path

    Provides validation and utility methods for path handling.
    """

    def __init__(self, path: str | Path):
        """Initialize with a path string or Path object"""
        self._path = Path(path).resolve()

    @property
    def path(self) -> Path:
        """Get the underlying Path object"""
        return self._path

    @property
    def absolute(self) -> str:
        """Get absolute path as string"""
        return str(self._path)

    @property
    def name(self) -> str:
        """Get file/folder name"""
        return self._path.name

    @property
    def stem(self) -> str:
        """Get file name without extension"""
        return self._path.stem

    @property
    def extension(self) -> str:
        """Get file extension (including dot)"""
        return self._path.suffix

    @property
    def parent(self) -> "FilePath":
        """Get parent directory as FilePath"""
        return FilePath(self._path.parent)

    def exists(self) -> bool:
        """Check if path exists"""
        return self._path.exists()

    def is_file(self) -> bool:
        """Check if path is a file"""
        return self._path.is_file()

    def is_dir(self) -> bool:
        """Check if path is a directory"""
        return self._path.is_dir()

    def relative_to(self, other: "FilePath") -> Optional[str]:
        """Get relative path to another FilePath"""
        try:
            return str(self._path.relative_to(other._path))
        except ValueError:
            return None

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"FilePath('{self._path}')"

    def __eq__(self, other) -> bool:
        if isinstance(other, FilePath):
            return self._path == other._path
        return False

    def __hash__(self) -> int:
        return hash(self._path)
