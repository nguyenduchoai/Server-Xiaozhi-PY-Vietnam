"""
Pay2s Signature Utilities

Provides HMAC-SHA256 signature creation and verification for Pay2s API.
Reference: https://docs.pay2s.vn/others/signature.html
"""

import hmac
import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def create_signature(data: dict[str, Any], secret_key: str) -> str:
    """
    Create HMAC-SHA256 signature for Pay2s request.
    
    Algorithm:
    1. Filter out signature fields
    2. Sort params alphabetically by key
    3. Create query string: key1=value1&key2=value2...
    4. HMAC-SHA256(query_string, secret_key)
    
    Args:
        data: Dictionary of request parameters
        secret_key: Pay2s secret key
        
    Returns:
        Hex-encoded HMAC-SHA256 signature
    """
    # Filter out signature-related fields
    excluded_keys = {'signature', 'm2signature', 'sig'}
    filtered = {k: v for k, v in data.items() if k not in excluded_keys and v is not None}
    
    # Sort alphabetically by key
    sorted_items = sorted(filtered.items())
    
    # Handle array values (bankAccounts)
    processed_items = []
    for key, value in sorted_items:
        if isinstance(value, list):
            # For arrays, use "Array" as value per Pay2s docs
            processed_items.append((key, "Array"))
        else:
            processed_items.append((key, str(value)))
    
    # Create raw string
    raw_string = '&'.join(f"{k}={v}" for k, v in processed_items)
    
    logger.debug(f"Signature raw string: {raw_string[:100]}...")
    
    # Calculate HMAC-SHA256
    signature = hmac.new(
        secret_key.encode('utf-8'),
        raw_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def verify_signature(data: dict[str, Any], secret_key: str) -> bool:
    """
    Verify HMAC-SHA256 signature from Pay2s callback (IPN/Webhook).
    
    Args:
        data: Dictionary containing the callback data with signature
        secret_key: Pay2s secret key
        
    Returns:
        True if signature is valid, False otherwise
    """
    # Get received signature
    received_sig = data.get('signature') or data.get('m2signature')
    
    if not received_sig:
        logger.warning("No signature found in Pay2s callback")
        return False
    
    # Calculate expected signature
    expected_sig = create_signature(data, secret_key)
    
    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_sig, received_sig)
    
    if not is_valid:
        logger.warning(
            f"Pay2s signature verification failed. "
            f"Expected: {expected_sig[:16]}..., Received: {received_sig[:16]}..."
        )
    
    return is_valid


def create_ipn_signature(data: dict[str, Any], secret_key: str) -> str:
    """
    Create signature specifically for IPN response verification.
    
    IPN uses specific fields for signature:
    - accessKey, amount, message, orderId, orderInfo, orderType, 
    - partnerCode, payType, requestId, responseTime, resultCode, transId
    
    Args:
        data: IPN callback data
        secret_key: Pay2s secret key
        
    Returns:
        Hex-encoded signature
    """
    # IPN signature fields (in alphabetical order per Pay2s docs)
    ipn_fields = [
        'accessKey', 'amount', 'message', 'orderId', 'orderInfo', 
        'orderType', 'partnerCode', 'payType', 'requestId', 
        'responseTime', 'resultCode', 'transId'
    ]
    
    # Build filtered data with only IPN fields
    filtered = {k: data.get(k, '') for k in ipn_fields if data.get(k) is not None}
    
    return create_signature(filtered, secret_key)
