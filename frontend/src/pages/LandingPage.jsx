import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Sparkles, ImagePlus, Eye, History, Wand2 } from 'lucide-react';
import Lenis from 'lenis';

export default function LandingPage() {
  useEffect(() => {
    // Initialize Lenis for smooth scrolling on landing page
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      direction: 'vertical',
      gestureDirection: 'vertical',
      smooth: true,
    });

    function raf(time) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    return () => {
      lenis.destroy();
    };
  }, []);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Hero Section */}
      <section style={{ 
        position: 'relative', 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        padding: '0 2rem',
        overflow: 'hidden'
      }}>
        {/* Background Image */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: 'url(/hero-bg.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.4,
          zIndex: -1,
          maskImage: 'linear-gradient(to bottom, black 50%, transparent 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, black 50%, transparent 100%)'
        }} />

        <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', zIndex: 1 }}>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1.2rem', background: 'rgba(0, 0, 0, 0.1)', border: '1px solid rgba(255, 255, 255, 0.15)', borderRadius: '30px', color: '#ffffff', marginBottom: '1.5rem', fontWeight: 500, textShadow: '0 1px 2px rgba(0,0,0,0.5)', boxShadow: '0 8px 16px rgba(0,0,0,0.2)' }}>
              <Sparkles size={16} color="var(--accent-primary)" />
              <span>Next-Gen Image Processing</span>
            </div>
            
            <h1 style={{ fontSize: '5rem', lineHeight: 1.1, marginBottom: '1.5rem', textShadow: '0 10px 30px rgba(0,0,0,0.8)' }}>
              Welcome to <br />
              <span className="text-gradient">ChromaVision</span>
            </h1>
            
            <p style={{ fontSize: '1.25rem', color: '#ffffff', maxWidth: '600px', margin: '0 auto 3rem', lineHeight: 1.6, textShadow: '0 2px 4px rgba(0,0,0,0.1), 0 4px 12px rgba(0,0,0,0.1)', fontWeight: 500, background: 'rgba(0,0,0,0.1)', padding: '1rem', borderRadius: '12px' }}>
              Unlock the true potential of your images. Enhance resolution, restore vintage photos, and simulate color vision deficiencies with state-of-the-art AI.
            </p>

            <Link to="/app" style={{ textDecoration: 'none' }}>
              <motion.button 
                className="glass-button primary"
                style={{ fontSize: '1.1rem', padding: '1rem 2.5rem', borderRadius: '16px' }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Launch App Dashboard
              </motion.button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Feature Showcase */}
      <section style={{ padding: '8rem 2rem', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4rem', alignItems: 'center' }}>
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8 }}
          >
            <h2 style={{ fontSize: '3rem', marginBottom: '1.5rem' }}>Breathe Life Into <br /><span style={{ color: 'var(--accent-secondary)' }}>Faded Memories</span></h2>
            <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', marginBottom: '2rem', lineHeight: 1.6 }}>
              Our advanced photo restoration neural network analyzes and reconstructs damaged, scratched, or sepia photos. Experience true high-definition clarity seamlessly.
            </p>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '1rem', color: 'var(--text-primary)' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}><Wand2 color="var(--accent-primary)"/> Colorize black and white photos</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}><History color="var(--accent-primary)"/> Repair scratches and damage</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}><ImagePlus color="var(--accent-primary)"/> Upscale faces up to 10x</li>
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8 }}
            className="glass-panel"
            style={{ padding: '1rem', background: 'linear-gradient(135deg, rgba(255,255,255,0.05), rgba(0,0,0,0.2))' }}
          >
            <img src="/restore-demo.png" alt="Restoration Demo" style={{ width: '100%', height: 'auto', borderRadius: '12px', display: 'block' }} />
          </motion.div>
        </div>
      </section>

      {/* Grid Features */}
      <section style={{ padding: '6rem 2rem 8rem', background: 'rgba(0,0,0,0.3)', borderTop: '1px solid var(--border-color)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <h2 style={{ textAlign: 'center', fontSize: '2.5rem', marginBottom: '4rem' }}>Powerful Tools Suite</h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
            {[
              { title: 'Color Blind Toolkit', desc: 'Simulate and daltonize images to improve accessibility for CVD.', icon: Eye, color: '#3b82f6' },
              { title: 'AI Colorize Pro', desc: 'Accurately predict and apply colors to old grayscale photos.', icon: Wand2, color: '#8b5cf6' },
              { title: 'Real-ESRGAN Upscale', desc: 'Increase image resolution significantly without losing quality.', icon: ImagePlus, color: '#10b981' }
            ].map((feat, i) => (
              <motion.div 
                key={i}
                className="glass-panel"
                style={{ padding: '2.5rem', textAlign: 'center' }}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                whileHover={{ y: -10, borderColor: feat.color }}
              >
                <div style={{ width: '60px', height: '60px', borderRadius: '16px', background: `${feat.color}20`, color: feat.color, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
                  <feat.icon size={30} />
                </div>
                <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>{feat.title}</h3>
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{feat.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <footer style={{ padding: '3rem 2rem', textAlign: 'center', borderTop: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
        <p>&copy; 2026 ChromaVision by DeepMatch. All rights reserved.</p>
      </footer>
    </div>
  );
}
