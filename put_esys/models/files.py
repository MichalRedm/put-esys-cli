from typing import List, Optional

from pydantic import BaseModel, Field


class PrivateFileItem(BaseModel):
    """Represents a file or directory in eKursy private files storage."""

    filename: str = Field(description="Name of the file or folder")
    filepath: str = Field(default="/", description="Directory path inside private files storage")
    fullname: str = Field(description="Display or full name of the item")
    size: int = Field(default=0, description="Size in bytes")
    filesize: str = Field(default="0 B", description="Formatted human-readable size")
    type: str = Field(default="file", description="Item type: 'file', 'folder', or 'zip'")
    url: Optional[str] = Field(default=None, description="Direct download URL if available")
    datemodified: Optional[int] = Field(default=None, description="Last modification timestamp")
    datecreated: Optional[int] = Field(default=None, description="Creation timestamp")
    author: Optional[str] = Field(default=None, description="Author metadata")
    license: Optional[str] = Field(default=None, description="License type")


class PrivateFilesList(BaseModel):
    """Collection of private files and subdirectories."""

    path: str = Field(default="/", description="Current directory path")
    items: List[PrivateFileItem] = Field(default_factory=list, description="Files and folders")
    file_count: int = Field(default=0, description="Total number of files")
    folder_count: int = Field(default=0, description="Total number of directories")
    total_size: int = Field(default=0, description="Total size in bytes")
