"""
Pay2s API Client

HTTP client for Pay2s payment gateway API.
Reference: https://docs.pay2s.vn/api/
"""

import httpx
import logging
from typing import Any, Optional
from dataclasses import dataclass

from .signature import create_signature

logger = logging.getLogger(__name__)


# API URLs
PAY2S_PRODUCTION_URL = "https://payment.pay2s.vn"
PAY2S_SANDBOX_URL = "https://sandbox-payment.pay2s.vn"
PAY2S_PARTNER_API_URL = "https://api-partner.pay2s.vn"


@dataclass
class Pay2sConfig:
    """Pay2s configuration"""
    partner_code: str
    access_key: str
    secret_key: str
    sandbox_mode: bool = True
    payment_timeout_minutes: int = 15
    bank_account_number: str = ""
    bank_id: str = ""  # ACB, VCB, TCB, etc.
    
    @property
    def api_url(self) -> str:
        return PAY2S_SANDBOX_URL if self.sandbox_mode else PAY2S_PRODUCTION_URL


class Pay2sClient:
    """
    Pay2s API Client
    
    Handles all API communication with Pay2s payment gateway.
    """
    
    def __init__(self, config: Pay2sConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client
    
    async def create_collection_link(
        self,
        order_id: str,
        request_id: str,
        amount: int,
        order_info: str,
        redirect_url: str,
        ipn_url: str,
        partner_name: str = "",
    ) -> dict[str, Any]:
        """
        Create a payment collection link.
        
        Reference: https://docs.pay2s.vn/api/collection-link.html
        
        Args:
            order_id: Unique order ID (max 64 bytes)
            request_id: Unique request ID
            amount: Amount in VND
            order_info: Transfer content (10-32 chars, alphanumeric only)
            redirect_url: URL to redirect after payment
            ipn_url: URL for IPN callback
            partner_name: Partner display name
            
        Returns:
            Pay2s API response containing payment URL
        """
        # Build request data
        data = {
            "accessKey": self.config.access_key,
            "partnerCode": self.config.partner_code,
            "partnerName": partner_name or self.config.partner_code,
            "requestId": request_id,
            "amount": amount,
            "orderId": order_id,
            "orderInfo": order_info,
            "orderType": "pay2s",
            "redirectUrl": redirect_url,
            "ipnUrl": ipn_url,
            "requestType": "pay2s",
        }
        
        # Add bank accounts if configured
        if self.config.bank_account_number and self.config.bank_id:
            data["bankAccounts"] = [
                {
                    "account_number": self.config.bank_account_number,
                    "bank_id": self.config.bank_id
                }
            ]
        
        # Create signature
        data["signature"] = create_signature(data, self.config.secret_key)
        
        # Make API call
        url = f"{self.config.api_url}/v1/gateway/api/create"
        
        logger.info(f"Creating Pay2s collection link for order {order_id}, amount {amount}")
        logger.debug(f"Pay2s request URL: {url}")
        
        try:
            response = await self.client.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Pay2s collection link created: {result.get('resultCode')}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Pay2s API error: {e.response.status_code} - {e.response.text}")
            raise Pay2sAPIError(f"API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Pay2s request error: {e}")
            raise Pay2sAPIError(f"Request error: {str(e)}") from e
    
    async def get_banks(self) -> dict[str, Any]:
        """
        Get list of supported banks.
        
        Reference: https://docs.pay2s.vn/api/bankcode.html
        
        Returns:
            Dictionary of bank codes and their info
        """
        url = f"{self.config.api_url}/v1/banks"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get Pay2s banks: {e}")
            return {}


class Pay2sAPIError(Exception):
    """Pay2s API error"""
    pass
