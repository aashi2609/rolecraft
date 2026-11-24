/**
 * Payment Processing Client
 *
 * This module handles client-side payment processing by communicating with the backend
 * Razorpay integration (STEP E - Payment Verification).
 *
 * Flow:
 * 1. Client calls processPayment() → backend creates a payment order
 *    (POST /payments/orders) and reports PAYMENTS_MODE.
 * 2. PAYMENTS_MODE=test (mock/demo): client calls POST /payments/mock-complete —
 *    no Razorpay checkout, no real charge; backend marks the transaction `mock_*`
 *    and activates through the same path as the verified webhook.
 * 3. PAYMENTS_MODE=live: client opens Razorpay Checkout, then POST /payments/verify
 *    confirms the signature; the server-to-server webhook activates the subscription.
 * 4. PAYMENTS_MODE=disabled: order creation returns 503 — no checkout at all.
 */

import { API_URL, getToken } from './api';

export type PlanId = 'basic' | 'complete' | 'job_search' | 'resume_builder' | 'corporate_annual' | 'corporate_lifetime';

export interface PaymentDetails {
  planId: PlanId;
  amount: number;
  currency: string;
  isAnnual: boolean;
  /** @deprecated Payment method/details are handled by the backend/provider;
   *  kept optional for backward compatibility. */
  paymentMethod?: string;
  paymentData?: Record<string, any>;
}

export interface PaymentResult {
  success: boolean;
  error?: string;
  orderId?: string;
  checkoutUrl?: string;
  /** True when the payment was completed via the PAYMENTS_MODE=test mock path. */
  mock?: boolean;
}

/**
 * Validates payment details before submission
 */
export function validatePaymentDetails(details: PaymentDetails): string | null {
  if (!details.planId) {
    return 'Plan selection is required';
  }

  if (!details.amount || details.amount <= 0) {
    return 'Invalid payment amount';
  }

  if (!details.currency) {
    return 'Currency is required';
  }

  // Validate based on payment method
  switch (details.paymentMethod) {
    case 'card':
      return validateCardDetails(details.paymentData ?? {});
    case 'upi':
      return validateUpiDetails(details.paymentData ?? {});
    case 'netbanking':
      return validateNetbankingDetails(details.paymentData ?? {});
    case 'wallet':
      return validateWalletDetails(details.paymentData ?? {});
    default:
      return 'Invalid payment method';
  }
}

function validateCardDetails(data: Record<string, any>): string | null {
  if (!data.cardNumber || !/^\d{13,19}$/.test(data.cardNumber.replace(/\s/g, ''))) {
    return 'Please enter a valid card number';
  }

  if (!data.expiry || !/^\d{2}\/\d{2}$/.test(data.expiry)) {
    return 'Please enter expiry in MM/YY format';
  }

  if (!data.cvv || !/^\d{3,4}$/.test(data.cvv)) {
    return 'Please enter a valid CVV';
  }

  if (!data.name || data.name.trim().length < 3) {
    return 'Please enter valid name on card';
  }

  return null;
}

function validateUpiDetails(data: Record<string, any>): string | null {
  if (!data.upiId || !/^[a-zA-Z0-9._-]+@[a-zA-Z]+$/.test(data.upiId)) {
    return 'Please enter a valid UPI ID (e.g., username@upi)';
  }
  return null;
}

function validateNetbankingDetails(data: Record<string, any>): string | null {
  if (!data.bank || data.bank.trim().length === 0) {
    return 'Please select a bank';
  }
  return null;
}

function validateWalletDetails(data: Record<string, any>): string | null {
  if (!data.wallet || data.wallet.trim().length === 0) {
    return 'Please select a wallet';
  }
  return null;
}

/**
 * Process payment through backend Razorpay integration
 *
 * This function:
 * 1. Sends payment details to backend
 * 2. Backend creates Razorpay order
 * 3. Opens Razorpay Checkout modal (client-side)
 * 4. Webhook handles signature verification + subscription activation
 */
export async function processPayment(details: PaymentDetails): Promise<PaymentResult> {
  try {
    const billingPeriod =
      details.planId === 'corporate_lifetime'
        ? 'lifetime'
        : details.isAnnual
          ? 'annual'
          : 'monthly';

    // Step 1: Create payment order via backend (POST /payments/orders)
    const orderResponse = await fetch(`${API_URL}/payments/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify({
        plan_tier: details.planId,
        billing_period: billingPeriod,
      }),
    });

    if (!orderResponse.ok) {
      const error = await orderResponse.json().catch(() => ({}));
      return {
        success: false,
        error: error.detail || error.message || 'Failed to create payment order',
      };
    }

    const orderData = await orderResponse.json();
    const { order_id, key, amount, email, mode } = orderData;

    // Step 2a: TEST/MOCK MODE — complete via the explicit mock endpoint.
    // No Razorpay checkout, no real charge; backend marks it mock_* and
    // activates through the same verified path as the real webhook.
    if (mode === 'test') {
      const mockResponse = await fetch(`${API_URL}/payments/mock-complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ order_id }),
      });

      if (!mockResponse.ok) {
        const error = await mockResponse.json().catch(() => ({}));
        return {
          success: false,
          error: error.detail || 'Mock payment completion failed',
        };
      }

      return { success: true, orderId: order_id, mock: true };
    }

    // Step 2b: LIVE MODE — open Razorpay Checkout
    return new Promise((resolve) => {
      const options = {
        key: key,
        amount: amount, // in paise
        currency: 'INR',
        name: 'RoleCraft',
        description: `${details.planId} plan subscription`,
        order_id: order_id,
        prefill: {
          email: email || '',
        },
        handler: async (response: any) => {
          // Step 3: Verify payment signature on backend
          try {
            const verifyResponse = await fetch(`${API_URL}/payments/verify`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`,
              },
              body: JSON.stringify({
                order_id: response.razorpay_order_id,
                payment_id: response.razorpay_payment_id,
                signature: response.razorpay_signature,
              }),
            });

            if (verifyResponse.ok) {
              resolve({ success: true, orderId: order_id });
            } else {
              const error = await verifyResponse.json().catch(() => ({}));
              resolve({
                success: false,
                error: error.detail || 'Payment verification failed',
              });
            }
          } catch {
            resolve({ success: false, error: 'Payment verification failed' });
          }
        },
        modal: {
          onclosed: () => {
            resolve({
              success: false,
              error: 'Payment was cancelled by user',
            });
          },
        },
      };

      // Load Razorpay script if not already loaded
      if (!(window as any).Razorpay) {
        const script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.onload = () => {
          const rzp = new (window as any).Razorpay(options);
          rzp.open();
        };
        script.onerror = () => {
          resolve({
            success: false,
            error: 'Failed to load payment gateway',
          });
        };
        document.body.appendChild(script);
      } else {
        const rzp = new (window as any).Razorpay(options);
        rzp.open();
      }
    });
  } catch (error) {
    console.error('Payment processing error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'An unexpected error occurred',
    };
  }
}

/**
 * Get authentication token — same key the API client uses.
 */
function getAuthToken(): string {
  if (typeof window === 'undefined') return '';
  return getToken() || '';
}

/**
 * Razorpay type declaration
 */
declare global {
  interface Window {
    Razorpay?: any;
  }
}
