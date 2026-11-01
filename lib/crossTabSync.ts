/**
 * Cross-tab synchronization via BroadcastChannel.
 * When user logs out in one tab, all other tabs are notified and also log out.
 */

type StorageEventCallback = (action: 'logout' | 'token_changed') => void;

let channel: BroadcastChannel | null = null;
let listeners: StorageEventCallback[] = [];

/**
 * Initialize cross-tab sync. Call once on app mount.
 */
export function initCrossTabSync(): void {
  if (!typeof window || typeof BroadcastChannel === 'undefined') {
    return; // BroadcastChannel not available
  }

  try {
    channel = new BroadcastChannel('rolecraft:auth');
    channel.onmessage = (event) => {
      const { action } = event.data;
      if (action === 'logout' || action === 'token_changed') {
        listeners.forEach(cb => cb(action));
      }
    };
  } catch (_e) {
    // BroadcastChannel may not be available in private browsing; fall back to storage events
    window.addEventListener('storage', (e) => {
      if (e.key === 'rolecraft_token') {
        if (!e.newValue) {
          // Token was removed — logout
          listeners.forEach(cb => cb('logout'));
        } else if (e.oldValue !== e.newValue) {
          // Token changed
          listeners.forEach(cb => cb('token_changed'));
        }
      }
    });
  }
}

/**
 * Notify other tabs of logout.
 */
export function broadcastLogout(): void {
  if (channel) {
    try {
      channel.postMessage({ action: 'logout' });
    } catch (e) {
      console.error('Failed to broadcast logout:', e);
    }
  }
  // Also update localStorage so storage event listeners pick it up
  try {
    localStorage.removeItem('rolecraft_token');
  } catch (e) {
    console.error('Failed to clear token:', e);
  }
}

/**
 * Subscribe to auth events from other tabs.
 */
export function onCrossTabAuthEvent(callback: StorageEventCallback): () => void {
  listeners.push(callback);
  return () => {
    listeners = listeners.filter(l => l !== callback);
  };
}

/**
 * Clean up cross-tab sync on unmount.
 */
export function cleanupCrossTabSync(): void {
  if (channel) {
    try {
      channel.close();
    } catch (e) {
      console.error('Failed to close BroadcastChannel:', e);
    }
    channel = null;
  }
  listeners = [];
}
