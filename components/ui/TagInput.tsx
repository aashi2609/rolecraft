"use client";

import React, { useState, KeyboardEvent } from 'react';
import { X } from 'lucide-react';

interface TagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function TagInput({ tags, onChange, placeholder = 'Add a tag...', className = '' }: TagInputProps) {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const newTag = inputValue.trim().replace(/,$/, '');
      if (newTag && !tags.includes(newTag)) {
        onChange([...tags, newTag]);
      }
      setInputValue('');
    } else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  const removeTag = (indexToRemove: number) => {
    onChange(tags.filter((_, index) => index !== indexToRemove));
  };

  return (
    <div className={`flex flex-wrap gap-2 p-2 bg-white border border-border-soft rounded-lg shadow-sm focus-within:ring-2 focus-within:ring-primary focus-within:border-transparent transition-shadow ${className}`}>
      {tags.map((tag, index) => (
        <span
          key={index}
          className="flex items-center gap-1 px-2.5 py-1 text-sm font-medium bg-brand-blue/10 text-blue-700 rounded-full"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(index)}
            className="text-blue-400 hover:text-blue-800 focus:outline-none"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </span>
      ))}
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={tags.length === 0 ? placeholder : ''}
        className="flex-grow px-1 py-1 text-sm text-ink bg-transparent border-none focus:outline-none min-w-[120px] placeholder:text-ink-muted"
      />
    </div>
  );
}
