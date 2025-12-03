"""
File storage abstraction - supports local and Azure storage
"""
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


class StorageBackend:
    """Abstract storage backend"""
    
    def save(self, file_path: str, content: bytes) -> str:
        """Save file and return URL"""
        raise NotImplementedError
    
    def retrieve(self, file_path: str) -> bytes:
        """Retrieve file content"""
        raise NotImplementedError
    
    def delete(self, file_path: str) -> bool:
        """Delete file"""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage - free alternative to Azure Storage"""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, file_path: str, content: bytes) -> str:
        """Save file locally"""
        full_path = self.base_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, "wb") as f:
            f.write(content)
        
        return str(full_path)
    
    def retrieve(self, file_path: str) -> bytes:
        """Retrieve file from local storage"""
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(full_path, "rb") as f:
            return f.read()
    
    def delete(self, file_path: str) -> bool:
        """Delete local file"""
        full_path = self.base_path / file_path
        
        if full_path.exists():
            full_path.unlink()
            return True
        
        return False
    
    def get_file_url(self, file_path: str) -> str:
        """Get file URL for serving"""
        return f"/api/v1/storage/{file_path}"


class StorageFactory:
    """Factory to create storage backend based on config"""
    
    @staticmethod
    def create(storage_type: str, config: dict) -> StorageBackend:
        """Create storage backend"""
        if storage_type == "local":
            return LocalStorage(config.get("local_storage_path", "./data"))
        elif storage_type == "azure":
            # Placeholder for Azure Storage implementation
            raise NotImplementedError("Azure Storage not yet implemented")
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
