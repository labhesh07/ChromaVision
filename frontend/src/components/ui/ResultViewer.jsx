import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Download, SlidersHorizontal, Activity } from 'lucide-react';

export default function ResultViewer({ resultUrl, originalUrl, metaText, qualityText, pipelineSteps }) {
  const [compareValue, setCompareValue] = useState(50);
  const dividerRef = useRef(null);

  if (!resultUrl) return null;

  const showCompare = originalUrl && resultUrl;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="glass-panel"
      style={{ padding: '2rem', marginTop: '2rem' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem', color: 'var(--accent-primary)' }}>Processing Result</h3>
          {metaText && <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{metaText}</p>}
          {qualityText && <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>{qualityText}</p>}
        </div>
        <a 
          href={resultUrl} 
          download="processed-image.png"
          className="glass-button primary"
          style={{ textDecoration: 'none' }}
        >
          <Download size={18} />
          Download
        </a>
      </div>

      {showCompare ? (
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>
            <SlidersHorizontal size={18} />
            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>Interactive Comparison</span>
          </div>
          
          <div style={{ 
            position: 'relative', 
            borderRadius: '12px', 
            overflow: 'hidden', 
            border: '1px solid var(--border-color)',
            userSelect: 'none',
            background: '#000'
          }}>
            {/* Original Image (Bottom layer) */}
            <img src={originalUrl} alt="Original" style={{ display: 'block', width: '100%', height: 'auto' }} />
            
            {/* Processed Image (Top layer, clipped) */}
            <div style={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              width: '100%', 
              height: '100%', 
              clipPath: `inset(0 ${100 - compareValue}% 0 0)`
            }}>
              <img src={resultUrl} alt="Processed" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'contain' }} />
            </div>

            {/* Divider Line */}
            <div 
              ref={dividerRef}
              style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                left: `${compareValue}%`,
                width: '2px',
                backgroundColor: 'var(--accent-primary)',
                transform: 'translateX(-50%)',
                boxShadow: '0 0 10px rgba(59, 130, 246, 0.8)',
                pointerEvents: 'none'
              }}
            >
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '30px',
                height: '30px',
                backgroundColor: 'var(--surface-color)',
                backdropFilter: 'blur(4px)',
                border: '2px solid var(--accent-primary)',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <div style={{ width: '12px', height: '2px', backgroundColor: 'var(--text-primary)', transform: 'rotate(90deg)' }} />
              </div>
            </div>

            {/* Range Input for Control */}
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={compareValue} 
              onChange={(e) => setCompareValue(e.target.value)}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                opacity: 0,
                cursor: 'col-resize'
              }}
            />
          </div>
        </div>
      ) : (
        <div style={{ marginBottom: '2rem', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)', background: '#000' }}>
          <img src={resultUrl} alt="Result" style={{ display: 'block', width: '100%', height: 'auto' }} />
        </div>
      )}

      {pipelineSteps && pipelineSteps.length > 0 && (
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '12px', border: '1px dashed var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--accent-secondary)' }}>
            <Activity size={18} />
            <h4 style={{ margin: 0, fontSize: '1.1rem' }}>Processing Pipeline</h4>
          </div>
          <ul style={{ margin: 0, paddingLeft: '1.5rem', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            {pipelineSteps.map((step, idx) => (
              <motion.li 
                key={idx} 
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.3 + idx * 0.1, ease: "easeOut" }}
                style={{ marginBottom: '0.5rem' }}
              >
                {step}
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  );
}
