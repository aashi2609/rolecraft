"use client";

import * as React from "react";
import * as PopoverPrimitive from "@radix-ui/react-popover";
import { Command } from "cmdk";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchableComboboxProps {
  options: string[];
  value: string | string[];
  onChange: (value: any) => void;
  placeholder?: string;
  multiSelect?: boolean;
}

export function SearchableCombobox({
  options,
  value,
  onChange,
  placeholder = "Select an option...",
  multiSelect = false,
}: SearchableComboboxProps) {
  const [open, setOpen] = React.useState(false);
  const [inputValue, setInputValue] = React.useState("");
  
  const selectedValues = multiSelect ? (Array.isArray(value) ? value : []) : (value ? [value as string] : []);
  
  const filteredOptions = options.filter(option => 
    option.toLowerCase().includes(inputValue.toLowerCase()) &&
    !selectedValues.includes(option)
  );

  const showAddOption = inputValue.trim().length > 0 && 
    !options.some(opt => opt.toLowerCase() === inputValue.trim().toLowerCase()) &&
    !selectedValues.some(val => val.toLowerCase() === inputValue.trim().toLowerCase());

  const handleSelect = (currentValue: string) => {
    if (multiSelect) {
      if (!selectedValues.includes(currentValue)) {
        onChange([...selectedValues, currentValue]);
      }
      setInputValue("");
    } else {
      onChange(currentValue);
      setOpen(false);
    }
  };

  const handleRemove = (valueToRemove: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (multiSelect) {
      onChange(selectedValues.filter(v => v !== valueToRemove));
    } else {
      onChange("");
    }
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <button
          type="button"
          role="combobox"
          aria-expanded={open}
          className="flex min-h-10 w-full items-center justify-between rounded-md border border-border bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <div className="flex flex-wrap gap-1 w-full overflow-hidden">
            {multiSelect ? (
              selectedValues.length > 0 ? (
                selectedValues.map((val) => (
                  <span key={val} className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-xs font-medium text-secondary-foreground">
                    {val}
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={(e) => handleRemove(val, e)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRemove(val, e as any);
                      }}
                      className="cursor-pointer hover:text-foreground/80 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 rounded-sm"
                    >
                      <X className="h-3 w-3" />
                    </div>
                  </span>
                ))
              ) : (
                <span className="text-muted-foreground">{placeholder}</span>
              )
            ) : (
              <span className={cn("truncate", !value && "text-muted-foreground")}>
                {value || placeholder}
              </span>
            )}
          </div>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50 ml-2" />
        </button>
      </PopoverPrimitive.Trigger>
      
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          className="z-50 w-[var(--radix-popover-trigger-width)] min-w-[200px] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 bg-background border-border"
        >
          <Command className="flex h-full w-full flex-col overflow-hidden bg-transparent" shouldFilter={false}>
            <div className="flex items-center border-b border-border px-3" cmdk-input-wrapper="">
              <input
                className="flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Search or type to add..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
              />
            </div>
            
            <Command.List className="max-h-[300px] overflow-y-auto overflow-x-hidden p-1">
              <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                {!showAddOption && "No results found."}
              </Command.Empty>
              
              <Command.Group>
                {filteredOptions.map((option) => (
                  <Command.Item
                    key={option}
                    value={option}
                    onSelect={() => handleSelect(option)}
                    className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none data-[disabled=true]:pointer-events-none data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground data-[disabled=true]:opacity-50 hover:bg-accent/50 hover:cursor-pointer"
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selectedValues.includes(option) ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {option}
                  </Command.Item>
                ))}
              </Command.Group>
              
              {showAddOption && (
                <Command.Group>
                  <Command.Item
                    value={inputValue}
                    onSelect={() => handleSelect(inputValue.trim())}
                    className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:cursor-pointer text-primary"
                  >
                    <span className="mr-2 h-4 w-4 font-bold flex items-center justify-center">+</span>
                    Add "{inputValue.trim()}"
                  </Command.Item>
                </Command.Group>
              )}
            </Command.List>
          </Command>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
