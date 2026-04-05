/**
 * 3-D pipe viewer using @react-three/fiber.
 *
 * Renders:
 *  - A tube following the pipe centreline (Three.js TubeGeometry)
 *  - Colour mapping by pressure (blue=low → red=high)
 *  - Switch between baseline and optimised geometry
 */
import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text } from '@react-three/drei'
import * as THREE from 'three'
import type { CFDResult, BentPipeGeometry } from '../../types'

// ── pressure colour scale ────────────────────────────────────────────────────

function pressureToColor(p: number, pMin: number, pMax: number): THREE.Color {
  const t = pMax > pMin ? (p - pMin) / (pMax - pMin) : 0.5
  // blue(low) → cyan → green → yellow → red(high)
  const colors = [
    new THREE.Color(0x0033ff),
    new THREE.Color(0x00ccff),
    new THREE.Color(0x00ff88),
    new THREE.Color(0xffdd00),
    new THREE.Color(0xff2200),
  ]
  const seg = (colors.length - 1) * t
  const i = Math.min(Math.floor(seg), colors.length - 2)
  const f = seg - i
  return colors[i].clone().lerp(colors[i + 1], f)
}

// ── tube mesh component ───────────────────────────────────────────────────────

interface TubeMeshProps {
  points: [number, number, number][]
  pressures: number[]
  radius: number
  label: string
  opacity?: number
}

function TubeMesh({ points, pressures, radius, label, opacity = 1 }: TubeMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null!)

  const { geometry } = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)))
    const geo = new THREE.TubeGeometry(curve, Math.max(points.length * 2, 64), radius, 16, false)

    // Colour vertices by pressure
    const pMin = Math.min(...pressures)
    const pMax = Math.max(...pressures)
    const count = geo.attributes.position.count
    const colours = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      // Map vertex index → arc segment
      const seg = Math.floor((i / count) * (pressures.length - 1))
      const c = pressureToColor(pressures[Math.min(seg, pressures.length - 1)], pMin, pMax)
      colours[i * 3 + 0] = c.r
      colours[i * 3 + 1] = c.g
      colours[i * 3 + 2] = c.b
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colours, 3))
    return { geometry: geo }
  }, [points, pressures, radius])

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial vertexColors transparent opacity={opacity} roughness={0.4} metalness={0.2} />
    </mesh>
  )
}

// ── colour legend ─────────────────────────────────────────────────────────────

function ColourLegend({ pMin, pMax }: { pMin: number; pMax: number }) {
  return (
    <group position={[0, -0.25, 0]}>
      {[0, 0.25, 0.5, 0.75, 1].map((t, i) => {
        const p = pMin + t * (pMax - pMin)
        const c = pressureToColor(p, pMin, pMax)
        return (
          <group key={i} position={[i * 0.12 - 0.24, 0, 0]}>
            <mesh>
              <boxGeometry args={[0.10, 0.02, 0.01]} />
              <meshBasicMaterial color={c} />
            </mesh>
            <Text position={[0, -0.025, 0]} fontSize={0.015} color="white" anchorX="center">
              {(p / 100).toFixed(0)}Pa
            </Text>
          </group>
        )
      })}
    </group>
  )
}

// ── main component ────────────────────────────────────────────────────────────

interface PipeViewer3DProps {
  baselineResult?: CFDResult
  optimizedResult?: CFDResult
  baselinePoints?: [number, number, number][]
  optimizedPoints?: [number, number, number][]
  geometry?: BentPipeGeometry
  showBoth?: boolean
}

export default function PipeViewer3D({
  baselineResult,
  optimizedResult,
  baselinePoints,
  optimizedPoints,
  geometry,
  showBoth = true,
}: PipeViewer3DProps) {
  const radius = (geometry?.diameter ?? 0.05) / 2

  const basePressures = baselineResult?.sections.pressure_pa ?? []
  const optPressures  = optimizedResult?.sections.pressure_pa ?? []

  const allPressures = [...basePressures, ...optPressures]
  const pMin = allPressures.length ? Math.min(...allPressures) : 0
  const pMax = allPressures.length ? Math.max(...allPressures) : 1

  const hasBaseline  = !!baselinePoints  && basePressures.length > 0
  const hasOptimized = !!optimizedPoints && optPressures.length > 0

  return (
    <Canvas
      camera={{ position: [0.4, 0.3, 0.6], fov: 45 }}
      style={{ background: '#0f172a', borderRadius: '0.75rem' }}
    >
      <ambientLight intensity={0.6} />
      <directionalLight position={[1, 2, 1]} intensity={1.2} />
      <directionalLight position={[-1, -1, -1]} intensity={0.4} />

      {hasBaseline && (
        <group position={[0, showBoth && hasOptimized ? 0.08 : 0, 0]}>
          <TubeMesh
            points={baselinePoints!}
            pressures={basePressures}
            radius={radius}
            label="Baseline"
            opacity={showBoth && hasOptimized ? 0.55 : 1}
          />
        </group>
      )}

      {hasOptimized && showBoth && (
        <group position={[0, -0.08, 0]}>
          <TubeMesh
            points={optimizedPoints!}
            pressures={optPressures}
            radius={radius}
            label="Optimised"
          />
        </group>
      )}

      {!hasBaseline && !hasOptimized && (
        <mesh>
          <boxGeometry args={[0.05, 0.05, 0.05]} />
          <meshStandardMaterial color="#334155" />
        </mesh>
      )}

      {allPressures.length > 0 && (
        <ColourLegend pMin={pMin} pMax={pMax} />
      )}

      <OrbitControls enableDamping dampingFactor={0.1} />
      <gridHelper args={[2, 20, '#1e293b', '#1e293b']} position={[0.3, -0.2, 0]} />
    </Canvas>
  )
}
