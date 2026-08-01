import React, { useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import FileUpload from '../ui/FileUpload';
import ResultViewer from '../ui/ResultViewer';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function ColorBlindTool() {
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('simulate');
  const [cvdType, setCvdType] = useState('deuteranopia');
  const [severity, setSeverity] = useState(1);
  const [strength, setStrength] = useState(1);
  
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
    formData.append('mode', mode);
    formData.append('cvd_type', cvdType);
    formData.append('severity', severity);
    formData.append('strength', strength);

    try {
      const response = await axios.post(`${API_BASE}/colorblind/process-json`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const { image, meta } = response.data;
      
      // Convert base64 to blob url
      const byteCharacters = atob(image);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'image/png' });
      const resultUrl = URL.createObjectURL(blob);
      
      const origUrl = URL.createObjectURL(file);
      setOriginalUrl(origUrl);

      // Format Meta
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
        <h2 style={{ marginBottom: '0.5rem' }}>Color Blind Simulator</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', fontSize: '0.95rem' }}>
          Simulate how an image may appear with CVD, or daltonize to boost separability for a chosen deficiency.
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <FileUpload file={file} setFile={setFile} />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Mode</label>
              <select className="glass-input" value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="simulate">Simulate CVD</option>
                <option value="daltonize">Daltonize</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Deficiency Type</label>
              <select className="glass-input" value={cvdType} onChange={(e) => setCvdType(e.target.value)}>
                <option value="protanopia">Protanopia (red absent)</option>
                <option value="deuteranopia">Deuteranopia (green absent)</option>
                <option value="tritanopia">Tritanopia (blue absent)</option>
                <option value="protanomaly">Protanomaly (red shifted)</option>
                <option value="deuteranomaly">Deuteranomaly (green shifted)</option>
                <option value="tritanomaly">Tritanomaly (blue shifted)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                <span>Severity</span>
                <span style={{ color: 'var(--accent-primary)' }}>{severity}</span>
              </label>
              <input 
                type="range" 
                min="0" max="1" step="0.05" 
                value={severity} 
                onChange={(e) => setSeverity(parseFloat(e.target.value))} 
                style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
              />
            </div>

            {mode === 'daltonize' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  <span>Daltonize Strength</span>
                  <span style={{ color: 'var(--accent-primary)' }}>{strength}</span>
                </label>
                <input 
                  type="range" 
                  min="0" max="3" step="0.1" 
                  value={strength} 
                  onChange={(e) => setStrength(parseFloat(e.target.value))} 
                  style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
                />
              </div>
            )}
          </div>

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
              'Process Image'
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
