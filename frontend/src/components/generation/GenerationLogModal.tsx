/**
 * GenerationLogModal - Sci-Fi styled live log display
 *
 * Shows real-time generation progress with terminal-style logs,
 * glowing effects, and particle explosion on completion.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'debug' | 'warn' | 'error' | 'success' | 'system';
  stage: string;
  message: string;
  progress?: number;
}

interface GenerationLogModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: LogEntry[];
  progress: number;
  stage: string;
  isComplete: boolean;
  isFailed: boolean;
  title?: string;
}

// Particle class for explosion effect
class Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
  color: string;

  constructor(x: number, y: number) {
    this.x = x;
    this.y = y;
    const angle = Math.random() * Math.PI * 2;
    const speed = Math.random() * 8 + 4;
    this.vx = Math.cos(angle) * speed;
    this.vy = Math.sin(angle) * speed;
    this.life = 1;
    this.maxLife = 1;
    this.size = Math.random() * 4 + 2;
    const colors = ['#00ff88', '#00ffff', '#ff00ff', '#ffff00', '#00ff00', '#ff6600'];
    this.color = colors[Math.floor(Math.random() * colors.length)];
  }

  update() {
    this.x += this.vx;
    this.y += this.vy;
    this.vy += 0.15; // gravity
    this.vx *= 0.99; // friction
    this.life -= 0.02;
  }

  draw(ctx: CanvasRenderingContext2D) {
    ctx.save();
    ctx.globalAlpha = this.life;
    ctx.fillStyle = this.color;
    ctx.shadowBlur = 10;
    ctx.shadowColor = this.color;
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size * this.life, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

export function GenerationLogModal({
  isOpen,
  onClose,
  logs,
  progress,
  stage,
  isComplete,
  isFailed,
  title = 'NEURAL PROCESSING',
}: GenerationLogModalProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationRef = useRef<number>();
  const [isExploding, setIsExploding] = useState(false);
  const [showContent, setShowContent] = useState(true);
  const hasExplodedRef = useRef(false);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setShowContent(true);
      setIsExploding(false);
      hasExplodedRef.current = false;
    }
  }, [isOpen]);

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Particle explosion effect
  const startExplosion = useCallback(() => {
    if (!canvasRef.current || hasExplodedRef.current) return;
    hasExplodedRef.current = true;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      // Can't animate, just close
      onClose();
      return;
    }

    // Set canvas size
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    // Create particles from center
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    particlesRef.current = [];
    for (let i = 0; i < 150; i++) {
      particlesRef.current.push(new Particle(centerX, centerY));
    }

    setIsExploding(true);
    setShowContent(false);

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particlesRef.current = particlesRef.current.filter(p => p.life > 0);

      for (const particle of particlesRef.current) {
        particle.update();
        particle.draw(ctx);
      }

      if (particlesRef.current.length > 0) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        // Animation complete, close modal immediately
        setIsExploding(false);
        onClose();
      }
    };

    animate();
  }, [onClose]);

  // Trigger explosion on completion
  useEffect(() => {
    if (isComplete && !isExploding && !hasExplodedRef.current && isOpen) {
      // Small delay to show completion message
      const timer = setTimeout(startExplosion, 800);
      return () => clearTimeout(timer);
    }
  }, [isComplete, isExploding, startExplosion, isOpen]);

  // Cleanup animation on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  // Get level color
  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error': return 'text-red-400';
      case 'warn': return 'text-yellow-400';
      case 'success': return 'text-green-400';
      case 'system': return 'text-cyan-400';
      case 'debug': return 'text-gray-500';
      default: return 'text-gray-300';
    }
  };

  const getLevelIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'error': return '[ERR]';
      case 'warn': return '[WRN]';
      case 'success': return '[OK!]';
      case 'system': return '[SYS]';
      case 'debug': return '[DBG]';
      default: return '[LOG]';
    }
  };

  // Early return if not open - ensures no overlay renders
  if (!isOpen) return null;

  // Handle backdrop click to close
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const modalContent = (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      onClick={handleBackdropClick}
    >
      {/* Backdrop with scanlines */}
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur-sm pointer-events-none"
        style={{
          backgroundImage: `repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 255, 136, 0.03) 2px,
            rgba(0, 255, 136, 0.03) 4px
          )`,
        }}
      />

      {/* Particle canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none z-10"
      />

      {/* Modal content */}
      {showContent && (
        <div
          className="relative z-[5] w-full max-w-4xl mx-4 animate-in fade-in zoom-in-95 duration-300"
          style={{
            animation: isComplete ? 'pulse 0.5s ease-in-out' : undefined,
          }}
        >
          {/* Outer glow frame */}
          <div
            className="absolute -inset-1 rounded-lg opacity-75 blur-sm"
            style={{
              background: isFailed
                ? 'linear-gradient(135deg, #ff0000, #ff4400, #ff0000)'
                : isComplete
                ? 'linear-gradient(135deg, #00ff88, #00ffff, #00ff88)'
                : 'linear-gradient(135deg, #00ff88, #0088ff, #ff00ff, #00ff88)',
              backgroundSize: '400% 400%',
              animation: 'gradient-shift 3s ease infinite',
            }}
          />

          {/* Main container */}
          <div className="relative bg-gray-900/95 rounded-lg border border-cyan-500/50 overflow-hidden">
            {/* Header */}
            <div className="relative px-6 py-4 border-b border-cyan-500/30">
              {/* Animated header background */}
              <div
                className="absolute inset-0 opacity-20"
                style={{
                  background: 'linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.3), transparent)',
                  backgroundSize: '200% 100%',
                  animation: 'shimmer 2s linear infinite',
                }}
              />

              <div className="relative flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* Animated icon */}
                  <div className="relative">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center"
                      style={{
                        background: 'linear-gradient(135deg, #00ff88, #00ffff)',
                        boxShadow: '0 0 20px rgba(0, 255, 136, 0.5)',
                      }}
                    >
                      {isComplete ? (
                        <svg className="w-6 h-6 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : isFailed ? (
                        <svg className="w-6 h-6 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      ) : (
                        <div className="w-5 h-5 border-2 border-gray-900 border-t-transparent rounded-full animate-spin" />
                      )}
                    </div>
                    {/* Pulse rings */}
                    {!isComplete && !isFailed && (
                      <>
                        <div className="absolute inset-0 rounded-lg animate-ping opacity-20 bg-cyan-400" />
                        <div className="absolute -inset-1 rounded-lg animate-pulse opacity-10 bg-cyan-400" />
                      </>
                    )}
                  </div>

                  <div>
                    <h2
                      className="text-xl font-mono font-bold tracking-wider"
                      style={{
                        color: '#00ff88',
                        textShadow: '0 0 10px rgba(0, 255, 136, 0.5)',
                      }}
                    >
                      {title}
                    </h2>
                    <p className="text-cyan-400/70 text-sm font-mono">
                      {isComplete ? 'SEQUENCE COMPLETE' : isFailed ? 'SEQUENCE FAILED' : stage.toUpperCase()}
                    </p>
                  </div>
                </div>

                {/* Close button - always visible */}
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors group"
                  title="Close and continue in background"
                >
                  <svg className="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Progress bar section */}
            {(() => {
              // Parse stage for diffusion/volume decoding progress
              const diffusionMatch = stage.match(/Diffusion\s*(?:Sampling)?:?\s*(\d+)\/(\d+)/i);
              const volumeMatch = stage.match(/Volume\s*(?:Decod(?:ing)?)?:?\s*(\d+)\/(\d+)/i);
              const activeMatch = diffusionMatch || volumeMatch;
              const isDiffusion = !!diffusionMatch;
              const isVolume = !!volumeMatch;

              if (activeMatch && !isComplete && !isFailed) {
                const current = parseInt(activeMatch[1]);
                const total = parseInt(activeMatch[2]);
                const stepProgress = current / total;
                const stageName = isDiffusion ? 'DIFFUSION SAMPLING' : 'VOLUME DECODING';
                const stageColor = isDiffusion ? '#ff00ff' : '#00ffff';

                return (
                  <div className="px-6 py-4 border-b border-cyan-500/20 bg-black/40">
                    {/* Stage header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        {/* Animated neural network icon */}
                        <div
                          className="w-8 h-8 rounded flex items-center justify-center"
                          style={{
                            background: `linear-gradient(135deg, ${stageColor}, transparent)`,
                            boxShadow: `0 0 15px ${stageColor}50`,
                          }}
                        >
                          <div className="w-4 h-4 border-2 rounded-full animate-spin" style={{ borderColor: stageColor, borderTopColor: 'transparent' }} />
                        </div>
                        <div>
                          <div
                            className="text-sm font-mono font-bold tracking-wider"
                            style={{ color: stageColor, textShadow: `0 0 10px ${stageColor}80` }}
                          >
                            {stageName}
                          </div>
                          <div className="text-xs text-gray-500 font-mono">
                            {isDiffusion ? 'Neural network inference' : 'Converting to 3D mesh'}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div
                          className="text-2xl font-mono font-bold tabular-nums"
                          style={{ color: stageColor, textShadow: `0 0 10px ${stageColor}80` }}
                        >
                          {current}<span className="text-gray-600">/{total}</span>
                        </div>
                        <div className="text-xs text-gray-500">STEPS</div>
                      </div>
                    </div>

                    {/* Step progress bar with segments */}
                    <div className="relative h-6 bg-gray-900 rounded overflow-hidden border border-gray-700">
                      {/* Segment markers */}
                      <div className="absolute inset-0 flex">
                        {Array.from({ length: Math.min(total, 25) }).map((_, i) => (
                          <div
                            key={i}
                            className="flex-1 border-r border-gray-800 last:border-r-0"
                          />
                        ))}
                      </div>
                      {/* Progress fill */}
                      <div
                        className="absolute inset-y-0 left-0 transition-all duration-300"
                        style={{
                          width: `${stepProgress * 100}%`,
                          background: `linear-gradient(90deg, ${stageColor}40, ${stageColor})`,
                          boxShadow: `0 0 20px ${stageColor}80, inset 0 0 10px ${stageColor}40`,
                        }}
                      >
                        {/* Scanning line effect */}
                        <div
                          className="absolute inset-0"
                          style={{
                            background: `linear-gradient(90deg, transparent, white, transparent)`,
                            animation: 'scan 1s linear infinite',
                          }}
                        />
                      </div>
                      {/* Glowing edge */}
                      <div
                        className="absolute inset-y-0 transition-all duration-300"
                        style={{
                          left: `${stepProgress * 100}%`,
                          width: '3px',
                          background: stageColor,
                          boxShadow: `0 0 10px ${stageColor}, 0 0 20px ${stageColor}`,
                        }}
                      />
                    </div>

                    {/* Progress percentage */}
                    <div className="flex justify-between mt-2 text-xs font-mono">
                      <span className="text-gray-500">STEP PROGRESS</span>
                      <span style={{ color: stageColor }}>{Math.round(stepProgress * 100)}%</span>
                    </div>
                  </div>
                );
              }

              // Default progress bar
              return (
                <div className="px-6 py-3 border-b border-cyan-500/20 bg-black/30">
                  <div className="flex items-center justify-between text-xs font-mono mb-2">
                    <span className="text-cyan-400">PROGRESS</span>
                    <span
                      className="tabular-nums"
                      style={{
                        color: '#00ff88',
                        textShadow: '0 0 5px rgba(0, 255, 136, 0.5)',
                      }}
                    >
                      {Math.round(progress * 100)}%
                    </span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className="h-full transition-all duration-300 relative"
                      style={{
                        width: `${progress * 100}%`,
                        background: isFailed
                          ? 'linear-gradient(90deg, #ff0000, #ff4400)'
                          : 'linear-gradient(90deg, #00ff88, #00ffff)',
                        boxShadow: isFailed
                          ? '0 0 10px rgba(255, 0, 0, 0.5)'
                          : '0 0 10px rgba(0, 255, 136, 0.5)',
                      }}
                    >
                      {/* Animated shine */}
                      <div
                        className="absolute inset-0"
                        style={{
                          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
                          animation: 'shimmer 1.5s linear infinite',
                        }}
                      />
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Log container */}
            <div
              ref={logContainerRef}
              className="h-80 overflow-y-auto px-6 py-4 font-mono text-sm"
              style={{
                background: 'linear-gradient(180deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.3) 100%)',
              }}
            >
              {logs.map((log, index) => (
                <div
                  key={log.id}
                  className={`flex gap-3 py-1 ${getLevelColor(log.level)} animate-in slide-in-from-left duration-200`}
                  style={{ animationDelay: `${index * 20}ms` }}
                >
                  <span className="text-gray-600 shrink-0">
                    {log.timestamp.toLocaleTimeString('en-US', {
                      hour12: false,
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                    <span className="text-gray-700">.{String(log.timestamp.getMilliseconds()).padStart(3, '0')}</span>
                  </span>
                  <span className={`shrink-0 ${getLevelColor(log.level)}`}>
                    {getLevelIcon(log.level)}
                  </span>
                  <span className="text-cyan-500/70 shrink-0">[{log.stage}]</span>
                  <span className="break-all">{log.message}</span>
                </div>
              ))}

              {/* Blinking cursor */}
              {!isComplete && !isFailed && (
                <div className="flex items-center gap-2 py-1 text-green-400">
                  <span className="animate-pulse">{'>'}</span>
                  <span className="w-2 h-4 bg-green-400 animate-blink" />
                </div>
              )}
            </div>

            {/* Footer stats */}
            <div className="px-6 py-3 border-t border-cyan-500/20 bg-black/30">
              <div className="flex items-center justify-between text-xs font-mono text-gray-500">
                <div className="flex items-center gap-4">
                  <span>LOGS: <span className="text-cyan-400">{logs.length}</span></span>
                  <span>STAGE: <span className="text-cyan-400">{stage}</span></span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isComplete ? 'bg-green-400' : isFailed ? 'bg-red-400' : 'bg-cyan-400 animate-pulse'
                    }`}
                  />
                  <span className={isComplete ? 'text-green-400' : isFailed ? 'text-red-400' : 'text-cyan-400'}>
                    {isComplete ? 'COMPLETE' : isFailed ? 'FAILED' : 'PROCESSING'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CSS Animations */}
      <style>{`
        @keyframes gradient-shift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes scan {
          0% { transform: translateX(-100%); opacity: 0; }
          50% { opacity: 0.6; }
          100% { transform: translateX(200%); opacity: 0; }
        }
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
        .animate-blink {
          animation: blink 1s step-end infinite;
        }
      `}</style>
    </div>
  );

  return createPortal(modalContent, document.body);
}

export default GenerationLogModal;
