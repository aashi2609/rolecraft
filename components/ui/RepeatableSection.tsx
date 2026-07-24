"use client";

import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from './Button';
import { Card } from './Card';

interface RepeatableSectionProps<T> {
  title: string;
  items: T[];
  onAdd: () => void;
  onRemove: (index: number) => void;
  renderItem: (item: T, index: number) => React.ReactNode;
  addLabel?: string;
}

export function RepeatableSection<T>({
  title,
  items,
  onAdd,
  onRemove,
  renderItem,
  addLabel = 'Add Item',
}: RepeatableSectionProps<T>) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold text-ink">{title}</h3>
      </div>
      
      {items.map((item, index) => (
        <Card key={index} className="relative !p-5">
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="absolute top-4 right-4 p-1.5 text-ink-muted hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
            title="Remove item"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          {renderItem(item, index)}
        </Card>
      ))}

      <Button
        type="button"
        variant="outline"
        onClick={onAdd}
        className="w-full border-dashed py-3"
      >
        <Plus className="w-4 h-4 mr-2" />
        {addLabel}
      </Button>
    </div>
  );
}
