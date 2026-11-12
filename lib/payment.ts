/**
 * Payment Processing Client
 *
 * This module handles client-side payment processing by communicating with the backend
 * Razorpay integration (STEP E - Payment Verification).
 *
 * Flow:
 * 1. Client collects payment details on checkout form
 * 2. Client calls processPayment() → backend creates Razorpay order
 * 3. Client opens Razorpay Checkout modal
 * 4. User completes payment in Razorpay
 * 5. Razorpay redirects with payment details
 * 6. Backend webhook verifies signature + activates subscription
 */

export type PlanId = 'basic' | 'complete' | 'job_search' | 'resume_builder' | 'corporate_annual' | 'corporate_lifetime';

export interface PaymentDetails {
  planId: PlanId;
  amount: number;
  currency: string;
  isAnnual: boolean;
  paymentMethod: string;
  paymentData: Record<string, any>;
}

export interface PaymentResult {
  success: boolean;
  error?: string;
  orderId?: string;
  checkoutUrl?: string;
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
      return validateCardDetails(details.paymentData);
    case 'upi':
      return validateUpiDetails(details.paymentData);
    case 'netbanking':
      return validateNetbankingDetails(details.paymentData);
    case 'wallet':
      return validateWalletDetails(details.paymentData);
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
    // Step 1: Create payment order via backend
    const orderResponse = await fetch('/api/payments/create-order', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify({
        planId: details.planId,
        billingPeriod: details.isAnnual ? 'annual' : 'monthly',
      }),
    });

    if (!orderResponse.ok) {
      const error = await orderResponse.json();
      return {
        success: false,
        error: error.message || 'Failed to create payment order',
      };
    }

    const orderData = await orderResponse.json();
    const { razorpay_order_id, razorpay_key_id, amount, currency, email, user_name } = orderData;

    // Step 2: Open Razorpay Checkout
    return new Promise((resolve) => {
      const options = {
        key: razorpay_key_id,
        amount: amount, // in paise
        currency: currency,
        name: 'RoleCraft',
        description: `${details.planId} plan subscription`,
        order_id: razorpay_order_id,
        prefill: {
          name: user_name || '',
          email: email || '',
          contact: '', // User can fill if needed
        },
        handler: async (response: any) => {
          // Step 3: Verify payment on backend (webhook)
          // Note: Signature verification happens in webhook handler
          // No client-side verification needed (happens server-side for security)

          resolve({
            success: true,
            orderId: razorpay_order_id,
          });
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
 * Get authentication token from localStorage
 */
function getAuthToken(): string {
  if (typeof window === 'undefined') return '';
  const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
  return token || '';
}

/**
 * Razorpay type declaration
 */
declare global {
  interface Window {
    Razorpay?: any;
  }
}
