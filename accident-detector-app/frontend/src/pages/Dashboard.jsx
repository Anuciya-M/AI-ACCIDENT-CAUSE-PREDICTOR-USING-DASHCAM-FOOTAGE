import React, { useState, useEffect, useRef } from 'react'
import { AlertCircle, AlertTriangle, Play, Pause, Volume2, SkipBack, SkipForward, Maximize2 } from 'lucide-react'
import apiService from '../services/api'

function Dashboard() {
    const [detectorStatus, setDetectorStatus] = useState(null)
    const [latestAnalysis, setLatestAnalysis] = useState(null)
    const [error, setError] = useState(null)
    const [isPlaying, setIsPlaying] = useState(false)
    const [riskLevel, setRiskLevel] = useState('low')
    const [loading, setLoading] = useState(true)
    const [framesProcessed, setFramesProcessed] = useState(0)
    const [avgLatency, setAvgLatency] = useState('--')
    const [streamFps, setStreamFps] = useState('--')
    const [systemLoad, setSystemLoad] = useState('--')
    const [newAlert, setNewAlert] = useState(null)
    const [statsLastHour, setStatsLastHour] = useState({
        total_alerts: 0,
        high_risk_events: 0,
        medium_risk_events: 0,
        low_risk_events: 0
    })
    const [soundEnabled, setSoundEnabled] = useState(false)
    const videoRef = useRef(null)
    const audioContextRef = useRef(null)

    useEffect(() => {
        const fetchData = async () => {
            try {
                const dataRes = await apiService.getDashboardData()
                const data = dataRes.data

                setDetectorStatus({
                    model_loaded: data.ai_ready,
                    device: data.device || 'Unknown',
                    gpu_available: data.gpu_available || false
                })

                setLatestAnalysis(data)
                setFramesProcessed(data.frames_processed || 0)
                setAvgLatency(data.avg_latency_ms ? `${data.avg_latency_ms.toFixed(1)} ms` : '--')
                setStreamFps(data.stream_fps ? `${data.stream_fps.toFixed(1)} fps` : '--')
                setSystemLoad(data.system_load || '--')
                setNewAlert(data.new_alert)
                setStatsLastHour(data.stats_last_hour || {
                    total_alerts: 0,
                    high_risk_events: 0,
                    medium_risk_events: 0,
                    low_risk_events: 0
                })

                if (data.risk_level === 'HIGH') {
                    setRiskLevel('high')
                } else if (data.risk_level === 'MEDIUM') {
                    setRiskLevel('medium')
                } else {
                    setRiskLevel('low')
                }

                setError(null)
            } catch (err) {
                console.error('Error fetching data:', err)
                setError('Failed to fetch dashboard information')
            } finally {
                setLoading(false)
            }
        }

        fetchData()
        const interval = setInterval(fetchData, 1000)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        if (!newAlert) return

        // Initialize audio context on first user interaction if needed
        const initAudioContext = () => {
            try {
                const AudioContext = window.AudioContext || window.webkitAudioContext
                if (!AudioContext) return null

                // Create new context if needed
                if (!audioContextRef.current) {
                    audioContextRef.current = new AudioContext()
                    console.log('AudioContext created')
                }
                return audioContextRef.current
            } catch (e) {
                console.error('Failed to create AudioContext:', e)
                return null
            }
        }

        const playAlertSound = async () => {
            try {
                const alertMessage = typeof newAlert === 'string' ? newAlert : newAlert?.message || ''
                console.log('🔊 Playing alert sound for:', alertMessage)

                let audioCtx = initAudioContext()
                if (!audioCtx) return

                // Resume context if suspended (browser autoplay policy)
                if (audioCtx.state === 'suspended') {
                    console.log('Resuming suspended AudioContext...')
                    await audioCtx.resume()
                }

                const currentTime = audioCtx.currentTime

                // Create master gain node for volume control
                const masterGain = audioCtx.createGain()
                masterGain.gain.setValueAtTime(0.4, currentTime)  // Increased volume
                masterGain.connect(audioCtx.destination)

                // Pattern 1: First beep - 880 Hz, 150ms
                const osc1 = audioCtx.createOscillator()
                const gain1 = audioCtx.createGain()
                osc1.type = 'sine'
                osc1.frequency.setValueAtTime(880, currentTime)
                gain1.gain.setValueAtTime(0.3, currentTime)
                osc1.connect(gain1)
                gain1.connect(masterGain)
                osc1.start(currentTime)
                osc1.stop(currentTime + 0.15)
                gain1.gain.linearRampToValueAtTime(0, currentTime + 0.15)

                // Pattern 2: Second beep - 1100 Hz, 150ms (delayed 200ms)
                const osc2 = audioCtx.createOscillator()
                const gain2 = audioCtx.createGain()
                osc2.type = 'sine'
                osc2.frequency.setValueAtTime(1100, currentTime + 0.2)
                gain2.gain.setValueAtTime(0.3, currentTime + 0.2)
                osc2.connect(gain2)
                gain2.connect(masterGain)
                osc2.start(currentTime + 0.2)
                osc2.stop(currentTime + 0.35)
                gain2.gain.linearRampToValueAtTime(0, currentTime + 0.35)

                // Pattern 3: Third beep - 1320 Hz, 150ms (delayed 400ms) for HIGH urgency
                const riskLevel = typeof newAlert === 'object' ? newAlert?.risk_level : 'MEDIUM'
                if (riskLevel === 'HIGH') {
                    const osc3 = audioCtx.createOscillator()
                    const gain3 = audioCtx.createGain()
                    osc3.type = 'sine'
                    osc3.frequency.setValueAtTime(1320, currentTime + 0.4)
                    gain3.gain.setValueAtTime(0.3, currentTime + 0.4)
                    osc3.connect(gain3)
                    gain3.connect(masterGain)
                    osc3.start(currentTime + 0.4)
                    osc3.stop(currentTime + 0.55)
                    gain3.gain.linearRampToValueAtTime(0, currentTime + 0.55)
                }
            } catch (err) {
                console.warn('❌ Audio alert error:', err)
            }
        }

        // Play sound immediately
        playAlertSound()
        setSoundEnabled(true)
        setTimeout(() => setSoundEnabled(false), 700)
    }, [newAlert])

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-center">
                    <div className="inline-block animate-spin">
                        <div className="h-12 w-12 border-4 border-blue-500 border-dashed rounded-full" />
                    </div>
                    <p className="mt-4 text-slate-400">Loading dashboard...</p>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="bg-red-900 border border-red-700 text-red-100 px-6 py-4 rounded-lg">
                <div className="flex items-center gap-2">
                    <AlertCircle size={20} />
                    <span>Error: {error}</span>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6 h-full animate-fadeIn p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatBox label="Frames Processed" value={`${framesProcessed}`} color="blue" />
                <StatBox label="Avg Latency" value={avgLatency} color="blue" />
                <StatBox label="Stream FPS" value={streamFps} color="blue" />
                <StatBox label="System Load" value={systemLoad} color="blue" />
            </div>

            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
                <h3 className="text-white text-lg font-bold mb-3">Detector Status</h3>
                <DetailRow label="Model" value={detectorStatus?.model_loaded ? 'Loaded' : 'Offline'} color={detectorStatus?.model_loaded ? 'text-green-400' : 'text-red-400'} />
                <DetailRow label="Device" value={detectorStatus?.device || 'Unknown'} />
                <DetailRow label="GPU" value={detectorStatus?.gpu_available ? 'Yes' : 'No'} color={detectorStatus?.gpu_available ? 'text-green-400' : 'text-yellow-400'} />
            </div>

            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
                <h3 className="text-white text-lg font-bold mb-3">Risk Alert</h3>
                <div className={`rounded-lg p-3 ${riskLevel === 'high' ? 'bg-red-900/40 border-red-500' : riskLevel === 'medium' ? 'bg-yellow-900/30 border-yellow-500' : 'bg-green-900/20 border-green-500'}`}>
                    <p className="text-white font-bold">{riskLevel.toUpperCase()} {soundEnabled ? '🔊' : ''}</p>
                    <p className="text-slate-300 text-sm">{riskLevel === 'high' ? 'High risk detected.' : riskLevel === 'medium' ? 'Monitor the environment.' : 'All clear.'}</p>
                    {newAlert && (
                        <p className="text-white text-sm mt-2 font-bold">🚨 {typeof newAlert === 'string' ? newAlert : newAlert?.message || ''}</p>
                    )}
                </div>
            </div>

            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
                <h3 className="text-white text-lg font-bold mb-3">Statistics (Last Hour)</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-slate-700 rounded p-2">
                        <p className="text-slate-400 text-xs">Total Alerts</p>
                        <p className="text-white text-xl font-bold">{statsLastHour.total_alerts}</p>
                    </div>
                    <div className="bg-red-900/30 rounded p-2">
                        <p className="text-slate-400 text-xs">High Risk</p>
                        <p className="text-red-400 text-xl font-bold">{statsLastHour.high_risk_events}</p>
                    </div>
                    <div className="bg-yellow-900/30 rounded p-2">
                        <p className="text-slate-400 text-xs">Medium Risk</p>
                        <p className="text-yellow-400 text-xl font-bold">{statsLastHour.medium_risk_events}</p>
                    </div>
                    <div className="bg-green-900/30 rounded p-2">
                        <p className="text-slate-400 text-xs">Low Risk</p>
                        <p className="text-green-400 text-xl font-bold">{statsLastHour.low_risk_events}</p>
                    </div>
                </div>
            </div>
        </div>
    )
}

function StatBox({ label, value, color }) {
    const palette = {
        blue: 'bg-blue-900/40 border-blue-600',
        green: 'bg-green-900/40 border-green-600',
        red: 'bg-red-900/40 border-red-600',
        yellow: 'bg-yellow-900/40 border-yellow-600',
    }

    return (
        <div className={`border p-4 rounded-lg ${palette[color]}`}>
            <p className="text-slate-400 text-sm">{label}</p>
            <p className="text-white text-2xl font-bold">{value}</p>
        </div>
    )
}

function DetailRow({ label, value, color = 'text-slate-300' }) {
    return (
        <div className="flex justify-between items-center py-1">
            <span className="text-slate-400">{label}</span>
            <span className={`font-mono ${color}`}>{value}</span>
        </div>
    )
}

export default Dashboard
