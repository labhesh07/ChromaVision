import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, Image as ImageIcon, X } from 'lucide-react';

export default function FileUpload({ file, setFile, accept = "image/jpeg,image/png,image/webp,image/avif", maxSizeMB = 10 }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const handleFile = (selectedFile) => {
    setError('');
    if (!selectedFile) return;
    
    // Check type
    if (!accept.split(',').includes(selectedFile.type)) {
      setError(`Invalid file type. Accepted: ${accept}`);
      return;
    }
    
    // Check size
    if (selectedFile.size > maxSizeMB * 1024 * 1024) {
      setError(`File too large. Maximum size is ${maxSizeMB}MB`);
      return;
    }

    setFile(selectedFile);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const clearFile = (e) => {
    e.stopPropagation();
    setFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', width: '100%' }}>
      <motion.div
        className={`glass-panel`}
        style={{
          border: isDragOver ? '2px dashed var(--accent-primary)' : '2px dashed var(--border-color)',
          padding: '2rem',
          textAlign: 'center',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
          transition: 'border-color 0.3s ease',
          backgroundColor: isDragOver ? 'rgba(59, 130, 246, 0.1)' : 'var(--surface-color)',
        }}
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        whileHover={{ scale: file ? 1 : 1.02 }}
        whileTap={{ scale: file ? 1 : 0.98 }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          style={{ display: 'none' }}
          onChange={(e) => handleFile(e.target.files[0])}
        />

        <AnimatePresence mode="wait">
          {!file ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}
            >
              <div style={{ 
                width: '60px', 
                height: '60px', 
                borderRadius: '50%', 
                background: 'rgba(59, 130, 246, 0.2)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: 'var(--accent-primary)'
              }}>
                <UploadCloud size={32} />
              </div>
              <div>
                <p style={{ fontWeight: 600, fontSize: '1.1rem', marginBottom: '0.25rem' }}>Click or drag image here</p>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Max size: {maxSizeMB}MB ({accept.replace(/image\//g, '')})</p>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="filled"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}
            >
              <div style={{ 
                width: '50px', 
                height: '50px', 
                borderRadius: '12px', 
                background: 'rgba(16, 185, 129, 0.2)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: 'var(--success)'
              }}>
                <ImageIcon size={24} />
              </div>
              <div style={{ textAlign: 'left', flex: 1 }}>
                <p style={{ fontWeight: 600, fontSize: '1rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '200px' }}>
                  {file.name}
                </p>
                <p style={{ color: 'var(--success)', fontSize: '0.85rem' }}>Ready to process</p>
              </div>
              <button
                onClick={clearFile}
                style={{
                  background: 'rgba(239, 68, 68, 0.2)',
                  color: 'var(--danger)',
                  border: 'none',
                  borderRadius: '50%',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                }}
              >
                <X size={16} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
      
      {error && (
        <motion.p 
          initial={{ opacity: 0, height: 0 }} 
          animate={{ opacity: 1, height: 'auto' }} 
          style={{ color: 'var(--danger)', fontSize: '0.9rem', marginTop: '0.5rem', textAlign: 'center' }}
        >
          {error}
        </motion.p>
      )}
    </div>
  );
}
