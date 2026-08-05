/**
 * Payment service for RoleCraft
 * Currently supports mock payment processing for development
 * Can be extended with real payment providers (Stripe, Razorpay, etc.)
 */

export interface PaymentDetails {
  planId: string;
  amount: number;
  currency: string;
  isAnnual: boolean;
  paymentMethod: 'card' | 'upi' | 'netbanking' | 'wallet';
  paymentData?: Record<string, unknown>;
}

export interface PaymentResult {
  success: boolean;
  transactionId?: string;
  error?: string;
}

/**
 * Process payment (mock implementation)
 * In production, this would integrate with Stripe, Razorpay, or similar
 */
export async function processPayment(details: PaymentDetails): Promise<PaymentResult> {
  // Simulate payment processing delay
  await new Promise((resolve) => setTimeout(resolve, 1500));

  // Mock success for development
  // In production, this would call actual payment gateway APIs
  const mockSuccess = Math.random() > 0.1; // 90% success rate for testing

  if (mockSuccess) {
    return {
      success: true,
      transactionId: `txn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };
  }

  return {
    success: false,
    error: 'Payment failed. Please try again or use a different payment method.',
  };
}

/**
 * Validate payment details before processing
 */
export function validatePaymentDetails(details: PaymentDetails): string | null {
  if (!details.planId) {
    return 'Plan ID is required';
  }

  if (details.amount <= 0) {
    return 'Invalid amount';
  }

  if (!details.paymentMethod) {
    return 'Payment method is required';
  }

  // Additional validation based on payment method
  if (details.paymentMethod === 'card') {
    const cardData = details.paymentData as Record<string, string> | undefined;
    if (!cardData?.cardNumber || !cardData.expiry || !cardData.cvv) {
      return 'Card details are incomplete';
    }
  }

  if (details.paymentMethod === 'upi') {
    const upiData = details.paymentData as Record<string, string> | undefined;
    if (!upiData?.upiId || !upiData.upiId.includes('@')) {
      return 'Invalid UPI ID';
    }
  }

  return null;
}

/**
 * Format amount for display
 */
export function formatPaymentAmount(amount: number, currency: string): string {
  if (currency === 'INR') {
    return `₹${amount.toLocaleString('en-IN')}`;
  }
  return `$${amount.toLocaleString('en-US')}`;
}

/**
 * Get supported payment methods
 */
export const SUPPORTED_PAYMENT_METHODS = [
  { id: 'card', label: 'Credit/Debit Card', icon: 'CreditCard' },
  { id: 'upi', label: 'UPI', icon: 'Smartphone' },
  { id: 'netbanking', label: 'Net Banking', icon: 'Landmark' },
  { id: 'wallet', label: 'Wallet', icon: 'Wallet' },
] as const;
