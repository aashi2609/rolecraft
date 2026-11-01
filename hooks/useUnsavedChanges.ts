import { useEffect } from 'react';

/**
 * Hook to warn users before navigating away from a form with unsaved changes.
 * Shows a browser confirmation dialog on page refresh or navigation.
 *
 * @param hasChanges - Whether the form has unsaved changes
 * @param message - Custom message for the confirmation dialog (optional)
 */
export function useUnsavedChanges(
  hasChanges: boolean,
  message: string = 'You have unsaved changes. Do you really want to leave?'
): void {
  useEffect(() => {
    if (!hasChanges) return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = message;
      return message;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasChanges, message]);
}
