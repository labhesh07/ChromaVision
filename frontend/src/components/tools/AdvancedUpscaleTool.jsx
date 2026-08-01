import React, { useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import FileUpload from '../ui/FileUpload';
import ResultViewer from '../ui/ResultViewer';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function AdvancedUpscaleTool() {
  const [file, setFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [originalUrl, setOriginalUrl] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE}/advanced-upscale/process-json`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const { image, meta } = response.data;
      
      const byteCharacters = atob(image);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const blob = new Blob([new Uint8Array(byteNumbers)], { type: 'image/png' });
      const resultUrl = URL.createObjectURL(blob);
      
      const origUrl = URL.createObjectURL(file);
      setOriginalUrl(origUrl);

      const inputMeta = meta.input || {};
      const outputMeta = meta.output || {};
      const metaText = `Size: ${(inputMeta.byte_size/1024/1024).toFixed(2)}MB -> ${(outputMeta.byte_size/1024/1024).toFixed(2)}MB | Res: ${inputMeta.width}x${inputMeta.height} -> ${outputMeta.width}x${outputMeta.height}`;

      setResult({
        resultUrl,
        metaText,
        pipelineSteps: meta.pipeline?.steps || []
      });

    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Processing failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div className="glass-panel" style={{ padding: '2rem' }}>
        <h2 style={{ marginBottom: '0.5rem' }}>Advanced Upscale Pro</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', fontSize: '0.95rem' }}>
          Photorealistic 10x Pipeline: Bypasses GFPGAN to prevent "anime face" alterations. Uses pure mathematical upscale + synthetic grain injection to preserve 100% original identity and texture.
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <FileUpload file={file} setFile={setFile} />

          {error && (
            <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger)', borderRadius: '8px', color: '#fca5a5' }}>
              {error}
            </div>
          )}

          <motion.button 
            type="submit" 
            className="glass-button primary" 
            disabled={!file || isLoading}
            style={{ width: '100%', padding: '1rem', marginTop: '0.5rem' }}
            whileTap={{ scale: (!file || isLoading) ? 1 : 0.98 }}
          >
            {isLoading ? (
              <><Loader2 className="animate-spin" size={20} /> Processing...</>
            ) : (
              'Advanced Upscale'
            )}
          </motion.button>
        </form>
      </div>

      {result && (
        <ResultViewer 
          resultUrl={result.resultUrl} 
          originalUrl={originalUrl} 
          metaText={result.metaText}
          pipelineSteps={result.pipelineSteps}
        />
      )}
    </div>
  );
}
