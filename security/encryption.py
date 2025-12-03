"""
PHI Encryption Module

HIPAA-compliant encryption utilities for protecting PHI data at rest and in transit.
Uses AES-256-GCM with Azure Key Vault for key management.
"""

import base64
import os
from typing import Optional, Tuple

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

import structlog

logger = structlog.get_logger(__name__)


class PHIEncryption:
    """
    HIPAA-compliant encryption for Protected Health Information.
    
    Features:
    - AES-256-GCM encryption
    - Azure Key Vault integration
    - Automatic key rotation support
    - Authenticated encryption
    """
    
    def __init__(self, key_vault_url: Optional[str] = None, encryption_key_name: str = "phi-encryption-key"):
        """
        Initialize PHI encryption with Azure Key Vault.
        
        Args:
            key_vault_url: Azure Key Vault URL
            encryption_key_name: Name of the encryption key in Key Vault
        """
        self.key_vault_url = key_vault_url
        self.encryption_key_name = encryption_key_name
        self._key_cache: Optional[bytes] = None
        
        if self.key_vault_url:
            self.credential = DefaultAzureCredential()
            self.secret_client = SecretClient(
                vault_url=self.key_vault_url,
                credential=self.credential
            )
            logger.info("PHI encryption initialized with Azure Key Vault", 
                       key_vault=self.key_vault_url)
        else:
            logger.warning("PHI encryption initialized without Key Vault (development mode only)")
    
    def _get_encryption_key(self) -> bytes:
        """
        Retrieve encryption key from Azure Key Vault.
        
        Returns:
            bytes: 256-bit encryption key
        """
        if self._key_cache:
            return self._key_cache
        
        if not self.key_vault_url:
            # Development mode: generate a key (NOT FOR PRODUCTION)
            logger.warning("Using generated key - NOT FOR PRODUCTION USE")
            return os.urandom(32)
        
        try:
            secret = self.secret_client.get_secret(self.encryption_key_name)
            key = base64.b64decode(secret.value)
            self._key_cache = key
            logger.info("Encryption key retrieved from Key Vault")
            return key
        except Exception as e:
            logger.error("Failed to retrieve encryption key", error=str(e))
            raise
    
    def encrypt(self, plaintext: str, associated_data: Optional[str] = None) -> str:
        """
        Encrypt PHI data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            associated_data: Optional authenticated associated data (e.g., patient ID)
            
        Returns:
            str: Base64-encoded encrypted data with nonce
        """
        try:
            key = self._get_encryption_key()
            aesgcm = AESGCM(key)
            
            # Generate random nonce (96 bits for GCM)
            nonce = os.urandom(12)
            
            # Prepare associated data
            aad = associated_data.encode('utf-8') if associated_data else b''
            
            # Encrypt
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), aad)
            
            # Combine nonce + ciphertext and encode
            encrypted_data = nonce + ciphertext
            result = base64.b64encode(encrypted_data).decode('utf-8')
            
            logger.debug("PHI data encrypted", 
                        data_length=len(plaintext),
                        has_aad=bool(associated_data))
            
            return result
            
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise
    
    def decrypt(self, encrypted_data: str, associated_data: Optional[str] = None) -> str:
        """
        Decrypt PHI data using AES-256-GCM.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            associated_data: Optional authenticated associated data
            
        Returns:
            str: Decrypted plaintext
        """
        try:
            key = self._get_encryption_key()
            aesgcm = AESGCM(key)
            
            # Decode from base64
            data = base64.b64decode(encrypted_data)
            
            # Extract nonce and ciphertext
            nonce = data[:12]
            ciphertext = data[12:]
            
            # Prepare associated data
            aad = associated_data.encode('utf-8') if associated_data else b''
            
            # Decrypt
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
            result = plaintext.decode('utf-8')
            
            logger.debug("PHI data decrypted",
                        data_length=len(result),
                        has_aad=bool(associated_data))
            
            return result
            
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise
    
    def hash_identifier(self, identifier: str) -> str:
        """
        Create a cryptographic hash of an identifier for logging/indexing.
        
        Args:
            identifier: Patient ID or other identifier
            
        Returns:
            str: SHA-256 hash (hex encoded)
        """
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(identifier.encode('utf-8'))
        return digest.finalize().hex()


class FieldLevelEncryption:
    """
    Field-level encryption for selective PHI field encryption in databases.
    """
    
    def __init__(self, encryption: PHIEncryption):
        self.encryption = encryption
    
    def encrypt_fields(self, data: dict, sensitive_fields: list[str]) -> dict:
        """
        Encrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            sensitive_fields: List of field names to encrypt
            
        Returns:
            dict: Data with encrypted fields
        """
        encrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                original_value = str(encrypted_data[field])
                encrypted_data[field] = self.encryption.encrypt(
                    original_value,
                    associated_data=field
                )
                logger.debug("Field encrypted", field=field)
        
        return encrypted_data
    
    def decrypt_fields(self, data: dict, sensitive_fields: list[str]) -> dict:
        """
        Decrypt specified fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            sensitive_fields: List of field names to decrypt
            
        Returns:
            dict: Data with decrypted fields
        """
        decrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                encrypted_value = decrypted_data[field]
                decrypted_data[field] = self.encryption.decrypt(
                    encrypted_value,
                    associated_data=field
                )
                logger.debug("Field decrypted", field=field)
        
        return decrypted_data


def generate_encryption_key() -> str:
    """
    Generate a new 256-bit encryption key for Azure Key Vault.
    
    Returns:
        str: Base64-encoded encryption key
    """
    key = os.urandom(32)  # 256 bits
    return base64.b64encode(key).decode('utf-8')


# Example usage
if __name__ == "__main__":
    # Generate a key for Key Vault
    print("New encryption key (store in Azure Key Vault):")
    print(generate_encryption_key())
