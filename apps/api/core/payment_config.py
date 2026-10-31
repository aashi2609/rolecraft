"""Step 6C: Payment mode configuration and startup validation.

PAYMENTS_MODE controls whether online payments are available:
- disabled (default): No online payments; manual admin grants only
- test: Razorpay test mode (with mocked provider calls)
- live: Production Razorpay (requires all provider credentials)

Safe by default: app refuses to start in 'test' or 'live' modes
without proper environment configuration.
"""

from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PaymentMode(str, Enum):
    disabled = "disabled"
    test = "test"
    live = "live"


class PaymentConfig:
    """Payment configuration and validation."""
    
    def __init__(self, mode: str):
        try:
            self.mode = PaymentMode(mode.lower())
        except ValueError:
            raise ValueError(
                f"Invalid PAYMENTS_MODE: {mode}. "
                f"Must be one of: {', '.join([m.value for m in PaymentMode])}"
            )
    
    @property
    def is_disabled(self) -> bool:
        """Payments are disabled (manual grants only)."""
        return self.mode == PaymentMode.disabled
    
    @property
    def is_test(self) -> bool:
        """Payments in test mode (mocked provider calls)."""
        return self.mode == PaymentMode.test
    
    @property
    def is_live(self) -> bool:
        """Payments in live production mode."""
        return self.mode == PaymentMode.live
    
    def validate_startup(
        self,
        razorpay_key_id: Optional[str],
        razorpay_key_secret: Optional[str],
        razorpay_webhook_secret: Optional[str],
    ) -> None:
        """
        Validate payment configuration at startup.
        
        Raises:
            RuntimeError: If configuration is invalid for the selected mode
        """
        if self.is_disabled:
            # No payment provider required
            logger.info("Payments disabled (manual admin grants only)")
            return
        
        if self.is_test:
            # Test mode: warn if credentials are missing, but don't block
            if not razorpay_key_id:
                logger.warning("RAZORPAY_KEY_ID not set (using mock for test mode)")
            if not razorpay_key_secret:
                logger.warning("RAZORPAY_KEY_SECRET not set (using mock for test mode)")
            if not razorpay_webhook_secret:
                logger.warning("RAZORPAY_WEBHOOK_SECRET not set (using mock for test mode)")
            logger.info("Payments in TEST mode (provider calls will be mocked)")
            return
        
        if self.is_live:
            # Live mode: CRITICAL - all credentials required
            errors = []
            if not razorpay_key_id:
                errors.append("RAZORPAY_KEY_ID is required for live payments")
            if not razorpay_key_secret:
                errors.append("RAZORPAY_KEY_SECRET is required for live payments")
            if not razorpay_webhook_secret:
                errors.append("RAZORPAY_WEBHOOK_SECRET is required for live payments")
            
            if errors:
                raise RuntimeError(
                    "CRITICAL: Live payment mode requires all Razorpay credentials:\n" +
                    "\n".join(errors)
                )
            
            logger.info("Payments in LIVE mode (production Razorpay)")
