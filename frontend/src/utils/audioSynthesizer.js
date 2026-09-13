/**
 * EcoSentinel Acoustic Engine & Web Audio Forensics
 * Supports direct WAV playback with graceful synthetic Web Audio fallback and real-time AnalyserNode.
 */

let globalAudioCtx = null;
let currentSource = null;
let currentAnalyser = null;

export function getAudioContext() {
  if (!globalAudioCtx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      globalAudioCtx = new AudioCtx();
    }
  }
  if (globalAudioCtx && globalAudioCtx.state === 'suspended') {
    globalAudioCtx.resume();
  }
  return globalAudioCtx;
}

export function stopCurrentAudio() {
  if (currentSource) {
    try {
      currentSource.stop();
      currentSource.disconnect();
    } catch {
      // Ignored if already stopped
    }
    currentSource = null;
  }
}

/**
 * Plays audio evidence for a given event type.
 * Tries loading the audio WAV file first, and falls back to Web Audio synthesis.
 * Calls onEnded callback when audio completes.
 * Returns { analyser, duration }
 */
export async function playEventAudio(eventType, onEnded) {
  stopCurrentAudio();
  const ctx = getAudioContext();
  if (!ctx) return null;

  const analyser = ctx.createAnalyser();
  analyser.fftSize = 256;
  currentAnalyser = analyser;

  // Determine WAV file and sound type
  const normalizedType = (eventType || '').toLowerCase();
  let wavPath = '/audio/chainsaw.wav';
  let isGunshot = false;
  let isOcean = false;

  if (normalizedType.includes('gun') || normalizedType.includes('poach')) {
    wavPath = '/audio/gunshot.wav';
    isGunshot = true;
  } else if (normalizedType.includes('ocean') || normalizedType.includes('vessel') || normalizedType.includes('fish')) {
    wavPath = '/audio/ocean_sonar.wav';
    isOcean = true;
  }

  // Attempt 1: Fetch and decode real WAV file
  try {
    const response = await fetch(wavPath);
    if (response.ok) {
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
      
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(analyser);
      analyser.connect(ctx.destination);

      source.onended = () => {
        if (currentSource === source) currentSource = null;
        if (onEnded) onEnded();
      };

      source.start(0);
      currentSource = source;
      return { analyser, duration: audioBuffer.duration };
    }
  } catch (err) {
    console.warn(`WAV file fetch failed (${wavPath}), using Web Audio synthesis:`, err);
  }

  // Attempt 2: Live Web Audio Synthesizer Fallback
  return synthesizeAcousticSignal(ctx, analyser, isGunshot, isOcean, onEnded);
}

function synthesizeAcousticSignal(ctx, analyser, isGunshot, isOcean, onEnded) {
  const masterGain = ctx.createGain();
  masterGain.connect(analyser);
  analyser.connect(ctx.destination);

  const now = ctx.currentTime;

  if (isGunshot) {
    // === Ballistic Gunshot Synthesis ===
    // 1. Initial Explosive Crack (White noise burst)
    const bufferSize = ctx.sampleRate * 0.12;
    const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const output = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      output[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.025));
    }
    const noise = ctx.createBufferSource();
    noise.buffer = noiseBuffer;

    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = 'bandpass';
    noiseFilter.frequency.setValueAtTime(3200, now);
    noiseFilter.Q.setValueAtTime(1.5, now);

    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(1.0, now);
    noiseGain.gain.exponentialRampToValueAtTime(0.01, now + 0.12);

    noise.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(masterGain);
    noise.start(now);

    // 2. Low-frequency concussive muzzle thump
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(120, now);
    osc.frequency.exponentialRampToValueAtTime(35, now + 0.25);

    const oscGain = ctx.createGain();
    oscGain.gain.setValueAtTime(0.8, now);
    oscGain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    osc.connect(oscGain);
    oscGain.connect(masterGain);
    osc.start(now);
    osc.stop(now + 0.4);

    // 3. Mountain Echo Reverb Tail
    const echoBuffer = ctx.createBuffer(1, ctx.sampleRate * 1.5, ctx.sampleRate);
    const echoData = echoBuffer.getChannelData(0);
    for (let i = 0; i < echoData.length; i++) {
      echoData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.45));
    }
    const echoSource = ctx.createBufferSource();
    echoSource.buffer = echoBuffer;

    const echoFilter = ctx.createBiquadFilter();
    echoFilter.type = 'lowpass';
    echoFilter.frequency.setValueAtTime(1200, now);

    const echoGain = ctx.createGain();
    echoGain.gain.setValueAtTime(0.0, now);
    echoGain.gain.setValueAtTime(0.35, now + 0.08);
    echoGain.gain.exponentialRampToValueAtTime(0.001, now + 1.8);

    echoSource.connect(echoFilter);
    echoFilter.connect(echoGain);
    echoGain.connect(masterGain);
    echoSource.start(now + 0.08);
    echoSource.stop(now + 1.9);

    setTimeout(() => { if (onEnded) onEnded(); }, 1900);
    currentSource = { stop: () => { masterGain.gain.setValueAtTime(0, ctx.currentTime); } };
    return { analyser, duration: 1.9 };

  } else if (isOcean) {
    // === Ocean Sonar & Diesel Marine Engine ===
    const duration = 2.5;
    // Low rumble oscillator
    const engineOsc = ctx.createOscillator();
    engineOsc.type = 'triangle';
    engineOsc.frequency.setValueAtTime(45, now);

    const engineGain = ctx.createGain();
    engineGain.gain.setValueAtTime(0.4, now);
    engineGain.gain.linearRampToValueAtTime(0.01, now + duration);

    engineOsc.connect(engineGain);
    engineGain.connect(masterGain);
    engineOsc.start(now);
    engineOsc.stop(now + duration);

    // Sonar Ping
    const pingOsc = ctx.createOscillator();
    pingOsc.type = 'sine';
    pingOsc.frequency.setValueAtTime(840, now + 0.2);

    const pingGain = ctx.createGain();
    pingGain.gain.setValueAtTime(0.0, now);
    pingGain.gain.setValueAtTime(0.65, now + 0.2);
    pingGain.gain.exponentialRampToValueAtTime(0.001, now + 1.4);

    pingOsc.connect(pingGain);
    pingGain.connect(masterGain);
    pingOsc.start(now + 0.2);
    pingOsc.stop(now + 1.5);

    setTimeout(() => { if (onEnded) onEnded(); }, duration * 1000);
    currentSource = { stop: () => { masterGain.gain.setValueAtTime(0, ctx.currentTime); } };
    return { analyser, duration };

  } else {
    // === Chainsaw 2-Stroke Motor Synthesis ===
    const duration = 3.2;
    // Dual saw oscillators detuned
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    osc1.type = 'sawtooth';
    osc2.type = 'sawtooth';
    osc1.frequency.setValueAtTime(115, now);
    osc2.frequency.setValueAtTime(232, now);

    // LFO throttle revving modulation
    const lfo = ctx.createOscillator();
    lfo.type = 'sine';
    lfo.frequency.setValueAtTime(2.2, now);

    const lfoGain = ctx.createGain();
    lfoGain.gain.setValueAtTime(25, now);
    lfo.connect(lfoGain);
    lfoGain.connect(osc1.frequency);
    lfoGain.connect(osc2.frequency);
    lfo.start(now);
    lfo.stop(now + duration);

    // Resonant bandpass filter
    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(2450, now);
    filter.Q.setValueAtTime(2.0, now);

    const chainGain = ctx.createGain();
    chainGain.gain.setValueAtTime(0.0, now);
    chainGain.gain.linearRampToValueAtTime(0.45, now + 0.15);
    chainGain.gain.setValueAtTime(0.45, now + duration - 0.3);
    chainGain.gain.linearRampToValueAtTime(0.001, now + duration);

    osc1.connect(filter);
    osc2.connect(filter);
    filter.connect(chainGain);
    chainGain.connect(masterGain);

    osc1.start(now);
    osc2.start(now);
    osc1.stop(now + duration);
    osc2.stop(now + duration);

    setTimeout(() => { if (onEnded) onEnded(); }, duration * 1000);
    currentSource = { stop: () => { masterGain.gain.setValueAtTime(0, ctx.currentTime); } };
    return { analyser, duration };
  }
}
