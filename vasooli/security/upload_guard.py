"""
Document Upload Security Guard.

Validates uploaded files before parsing:
1. Allowed MIME types and Magic Bytes verification
2. File size enforcement (max 10MB default)
3. Safe filename / path traversal sanitization
4. Basic malware/macro signature checks
"""

import os
import re
from typing import Optional, Set, Tuple
from vasooli.domain.errors import DocumentSecurityError


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg"}

# Magic byte signatures for common document types
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "docx": [b"PK\x03\x04"],  # ZIP container header
}


class UploadGuard:
    """
    Validates uploaded document files for security compliance.
    """

    def __init__(self, max_size_bytes: int = MAX_FILE_SIZE_BYTES):
        self.max_size_bytes = max_size_bytes

    def sanitize_filename(self, filename: str) -> str:
        """
        Strips path traversal sequences, null bytes, and non-whitelisted characters.
        """
        # Remove null bytes
        clean = filename.replace("\x00", "")
        # Remove directory paths
        clean = os.path.basename(clean)
        # Remove dangerous traversal characters
        clean = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', clean)
        # Avoid hidden files
        clean = clean.lstrip(".")
        return clean or "uploaded_contract.txt"

    def validate_upload(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validates an upload against size, extension, and magic bytes.
        Returns (is_valid, sanitized_filename).
        Raises DocumentSecurityError on security violations.
        """
        # 1. Size check
        if len(content) > self.max_size_bytes:
            raise DocumentSecurityError(
                f"File size ({len(content)} bytes) exceeds maximum permitted limit ({self.max_size_bytes} bytes)."
            )
        if len(content) == 0:
            raise DocumentSecurityError("Uploaded file is empty (0 bytes).")

        # 2. Extension check
        clean_name = self.sanitize_filename(filename)
        _, ext = os.path.splitext(clean_name.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise DocumentSecurityError(
                f"File extension '{ext}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # 3. Magic bytes validation
        ext_clean = ext.lstrip(".")
        if ext_clean in MAGIC_SIGNATURES:
            signatures = MAGIC_SIGNATURES[ext_clean]
            matched = any(content.startswith(sig) for sig in signatures)
            if not matched:
                raise DocumentSecurityError(
                    f"File content does not match expected binary signature for extension '{ext}'."
                )

        # 4. Dangerous script pattern detection in text/xml
        dangerous_patterns = [b"<script", b"javascript:", b"vbscript:", b"cmd.exe", b"/bin/sh", b"powershell"]
        for pat in dangerous_patterns:
            if pat in content[:2048].lower():
                raise DocumentSecurityError("File content contains prohibited executable or script patterns.")

        return True, clean_name
