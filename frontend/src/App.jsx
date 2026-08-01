import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Lenis from 'lenis';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, ImagePlus, History, Maximize, Wand2 } from 'lucide-react';
import './index.css';

// Import tool components (we will create these next)
import ColorBlindTool from './components/tools/ColorBlindTool';
import ColorizeTool from './components/tools/ColorizeTool';
import RestoreTool from './components/tools/RestoreTool';
import UpscaleTool from './components/tools/UpscaleTool';
import AdvancedUpscaleTool from './components/tools/AdvancedUpscaleTool';
import LandingPage from './pages/LandingPage';

const TABS = [
  { id: 'cvd', label: 'Color Blind', icon: Eye, component: ColorBlindTool },
  { id: 'colorize', label: 'Colorize Pro', icon: Wand2, component: ColorizeTool },
  { id: 'restore', label: 'Old Photo Restore', icon: History, component: RestoreTool },
  { id: 'upscale', label: 'Upscale', icon: Maximize, component: UpscaleTool },
  { id: 'advupscale', label: 'Advanced Upscale', icon: ImagePlus, component: AdvancedUpscaleTool },
];

function AppDashboard() {
  const [activeTab, setActiveTab] = useState(TABS[0].id);

  useEffect(() => {
    // Initialize Lenis smooth scroll
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      direction: 'vertical',
      gestureDirection: 'vertical',
      smooth: true,
      mouseMultiplier: 1,
      smoothTouch: false,
      touchMultiplier: 2,
      infinite: false,
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

  const ActiveComponent = TABS.find(t => t.id === activeTab)?.component || TABS[0].component;

  return (
    <div className="app-container" style={{ padding: '2rem 1rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <Link to="/" style={{ textDecoration: 'none' }}>
          <motion.h1 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            style={{ fontSize: '3rem', marginBottom: '0.5rem', cursor: 'pointer' }}
          >
            <span className="text-gradient">ChromaVision</span>
          </motion.h1>
        </Link>
        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}
        >
          Premium Color Vision Tools, Photo Restoration, and Upscaling
        </motion.p>
      </header>

      <nav style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '3rem' }}>
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <motion.button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`glass-button ${isActive ? 'primary' : ''}`}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Icon size={18} />
              {tab.label}
            </motion.button>
          );
        })}
      </nav>

      <main>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: -20, filter: 'blur(10px)' }}
            animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
            exit={{ opacity: 0, x: 20, filter: 'blur(10px)' }}
            transition={{ duration: 0.4 }}
          >
            <ActiveComponent />
          </motion.div>
        </AnimatePresence>
      </main>

      <footer style={{ marginTop: '5rem', textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem 0', borderTop: '1px solid var(--border-color)' }}>
        <p>GPU recommended for restore and upscale. Place weights under <code>weights/</code>.</p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app" element={<AppDashboard />} />
      </Routes>
    </Router>
  );
}
