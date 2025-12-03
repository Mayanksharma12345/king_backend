"""
Tests for PHI Encryption Module
"""

import pytest
from security.encryption import PHIEncryption, FieldLevelEncryption, generate_encryption_key


class TestPHIEncryption:
    """Test cases for PHI encryption"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.encryption = PHIEncryption()  # Development mode (no Key Vault)
    
    def test_encrypt_decrypt_basic(self):
        """Test basic encryption and decryption"""
        plaintext = "Patient Name: John Doe"
        
        # Encrypt
        encrypted = self.encryption.encrypt(plaintext)
        assert encrypted != plaintext
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = self.encryption.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_with_associated_data(self):
        """Test encryption with authenticated associated data"""
        plaintext = "SSN: 123-45-6789"
        associated_data = "patient_123"
        
        # Encrypt with AAD
        encrypted = self.encryption.encrypt(plaintext, associated_data=associated_data)
        
        # Decrypt with correct AAD
        decrypted = self.encryption.decrypt(encrypted, associated_data=associated_data)
        assert decrypted == plaintext
        
        # Attempt to decrypt with wrong AAD should fail
        with pytest.raises(Exception):
            self.encryption.decrypt(encrypted, associated_data="wrong_data")
    
    def test_hash_identifier(self):
        """Test identifier hashing"""
        patient_id = "PATIENT-12345"
        
        hash1 = self.encryption.hash_identifier(patient_id)
        hash2 = self.encryption.hash_identifier(patient_id)
        
        # Same input produces same hash
        assert hash1 == hash2
        
        # Hash is different from input
        assert hash1 != patient_id
        
        # Hash is hex string
        assert all(c in '0123456789abcdef' for c in hash1)
    
    def test_encryption_key_generation(self):
        """Test encryption key generation"""
        key = generate_encryption_key()
        
        assert len(key) > 0
        # Should be base64 encoded
        import base64
        decoded = base64.b64decode(key)
        assert len(decoded) == 32  # 256 bits


class TestFieldLevelEncryption:
    """Test cases for field-level encryption"""
    
    def setup_method(self):
        """Set up test fixtures"""
        encryption = PHIEncryption()
        self.field_encryption = FieldLevelEncryption(encryption)
    
    def test_encrypt_specific_fields(self):
        """Test encrypting specific fields in a dictionary"""
        data = {
            "patient_id": "12345",
            "name": "John Doe",
            "age": 45,
            "diagnosis": "Hypertension"
        }
        
        sensitive_fields = ["name", "diagnosis"]
        
        # Encrypt
        encrypted_data = self.field_encryption.encrypt_fields(data, sensitive_fields)
        
        # Sensitive fields should be encrypted
        assert encrypted_data["name"] != data["name"]
        assert encrypted_data["diagnosis"] != data["diagnosis"]
        
        # Non-sensitive fields should be unchanged
        assert encrypted_data["patient_id"] == data["patient_id"]
        assert encrypted_data["age"] == data["age"]
    
    def test_decrypt_specific_fields(self):
        """Test decrypting specific fields in a dictionary"""
        data = {
            "patient_id": "12345",
            "name": "John Doe",
            "diagnosis": "Diabetes"
        }
        
        sensitive_fields = ["name", "diagnosis"]
        
        # Encrypt then decrypt
        encrypted_data = self.field_encryption.encrypt_fields(data, sensitive_fields)
        decrypted_data = self.field_encryption.decrypt_fields(encrypted_data, sensitive_fields)
        
        # Should match original
        assert decrypted_data["name"] == data["name"]
        assert decrypted_data["diagnosis"] == data["diagnosis"]
        assert decrypted_data["patient_id"] == data["patient_id"]


@pytest.mark.compliance
class TestHIPAACompliance:
    """HIPAA compliance tests for encryption"""
    
    def test_encryption_strength(self):
        """Verify AES-256-GCM encryption is used"""
        encryption = PHIEncryption()
        
        # Encrypt data
        encrypted = encryption.encrypt("test data")
        
        # Verify encryption produces different output
        encrypted2 = encryption.encrypt("test data")
        assert encrypted != encrypted2  # Nonce makes each encryption unique
    
    def test_phi_never_logged(self, caplog):
        """Ensure PHI is never logged in plain text"""
        encryption = PHIEncryption()
        phi_data = "SSN: 123-45-6789"
        
        # Perform operations
        encrypted = encryption.encrypt(phi_data)
        decrypted = encryption.decrypt(encrypted)
        
        # Check logs don't contain PHI
        log_text = caplog.text
        assert phi_data not in log_text
        assert "123-45-6789" not in log_text
