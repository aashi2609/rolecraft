import React from 'react';
import Link from 'next/link';

export interface SwapCTAAction {
  label: string;
  href?: string;
  onClick?: () => void;
  isActive?: boolean;
}

interface SwapCTAGroupProps {
  action1: SwapCTAAction;
  action2: SwapCTAAction;
  className?: string;
}

export function SwapCTAGroup({ action1, action2, className = '' }: SwapCTAGroupProps) {
  // If neither has isActive explicitly set, default action1 to active.
  const is1Active = action1.isActive ?? (action2.isActive === true ? false : true);
  const is2Active = action2.isActive ?? (is1Active ? false : true);

  const renderButton = (action: SwapCTAAction, isActive: boolean) => {
    const btnClass = `btn ${isActive ? 'is-primary' : 'is-secondary'}`;
    
    if (action.href) {
      return (
        <Link href={action.href} className={btnClass} onClick={action.onClick}>
          {action.label}
        </Link>
      );
    }
    
    return (
      <button className={btnClass} onClick={action.onClick}>
        {action.label}
      </button>
    );
  };

  return (
    <div className={`cta-group ${className}`}>
      {renderButton(action1, is1Active)}
      {renderButton(action2, is2Active)}
    </div>
  );
}
