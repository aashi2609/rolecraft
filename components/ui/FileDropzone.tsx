"use client";

import React, { useState, useRef } from 'react';
import { UploadCloud, File, X } from 'lucide-react';

interface FileDropzoneProps {
  onFileSelect: (file: File | null) => void;
  accept?: string;
  maxSizeMB?: number;
  className?: string;
}

export function FileDropzone({ onFileSelect, accept = '*/*', maxSizeMB = 5, className = '' }: FileDropzoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = (file: File) => {
    if (file.size > maxSizeMB * 1024 * 1024) {
      alert(`File size exceeds ${maxSizeMB}MB`);
      return;
    }
    setSelectedFile(file);
    onFileSelect(file);
  };

  const removeFile = () => {
    setSelectedFile(null);
    onFileSelect(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <div className={`w-full ${className}`}>
      {!selectedFile ? (
        <div
          className={`relative flex flex-col items-center justify-center w-full p-6 border-2 border-dashed rounded-xl transition-colors cursor-pointer ${
            dragActive ? 'border-primary bg-brand-blue/10' : 'border-border-soft bg-surface-soft hover:bg-surface-soft hover:border-ink-muted'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <UploadCloud className="w-10 h-10 text-ink-muted mb-3" />
          <p className="text-sm font-semibold text-ink">Click to upload or drag and drop</p>
          <p className="text-xs text-ink-muted mt-1">SVG, PNG, JPG or PDF (max. {maxSizeMB}MB)</p>
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept={accept}
            onChange={handleChange}
          />
        </div>
      ) : (
        <div className="flex items-center justify-between p-4 bg-white border border-border-soft rounded-xl shadow-sm">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-brand-blue/10 rounded-lg">
              <File className="w-6 h-6 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium text-ink truncate max-w-[200px]">{selectedFile.name}</p>
              <p className="text-xs text-ink-muted">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          </div>
          <button
            type="button"
            onClick={removeFile}
            className="p-1 text-ink-muted hover:text-red-500 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
}
