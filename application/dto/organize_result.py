"""Data Transfer Objects for organize operations"""
from dataclasses import dataclass
from typing import List


@dataclass
class OrganizeResult:
    """Result of organize operation"""
    success: bool
    files_moved: int
    files_renamed: int
    errors: List[str]
    target_directory: str

    def __str__(self) -> str:
        if self.success:
            return f"Successfully organized {self.files_moved} files"
        else:
            return f"Organization failed: {len(self.errors)} errors"
