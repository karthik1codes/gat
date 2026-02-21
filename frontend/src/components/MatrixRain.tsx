import { useEffect, useRef } from 'react'

/**
 * Crisp, high-resolution Matrix-style binary rain on canvas.
 * Renders sharp 0/1 digits so the login background stays clear (no blurry GIF).
 */
export default function MatrixRain() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId: number
    const chars = '01'
    const colCount = 45
    const fontSize = 14
    const baseSpeed = 1.2
    const green = '#00ff41'
    const greenDim = 'rgba(0, 255, 65, 0.15)'

    type Column = { y: number; speed: number; chars: string[] }
    const columns: Column[] = []

    const setSize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = window.innerWidth
      const h = window.innerHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.font = `${fontSize}px "SF Mono", "Monaco", "Consolas", monospace`
    }

    const initColumns = () => {
      columns.length = 0
      const w = window.innerWidth
      const spacing = w / colCount
      for (let i = 0; i < colCount; i++) {
        const len = 12 + Math.floor(Math.random() * 18)
        const charsArr: string[] = []
        for (let j = 0; j < len; j++) {
          charsArr.push(chars[Math.floor(Math.random() * chars.length)])
        }
        columns.push({
          y: Math.random() * -window.innerHeight,
          speed: baseSpeed + Math.random() * 1.5,
          chars: charsArr,
        })
      }
    }

    const draw = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      const spacing = w / colCount

      ctx.fillStyle = 'rgba(0, 0, 0, 0.06)'
      ctx.fillRect(0, 0, w, h)

      columns.forEach((col, i) => {
        const x = i * spacing + spacing * 0.3
        col.chars.forEach((char, j) => {
          const y = col.y + j * fontSize
          if (y < -fontSize || y > h + fontSize) return
          const isHead = j === col.chars.length - 1
          ctx.fillStyle = isHead ? '#fff' : j < col.chars.length - 3 ? greenDim : green
          ctx.fillText(char, x, y)
        })
        col.y += col.speed
        if (col.y > h + col.chars.length * fontSize) {
          col.y = -col.chars.length * fontSize
          col.chars = Array.from({ length: col.chars.length }, () =>
            chars[Math.floor(Math.random() * chars.length)]
          )
        }
      })

      animationId = requestAnimationFrame(draw)
    }

    setSize()
    initColumns()
    draw()

    const onResize = () => {
      setSize()
      initColumns()
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animationId)
      window.removeEventListener('resize', onResize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full z-0"
      style={{ display: 'block', imageRendering: 'crisp-edges' }}
      aria-hidden
    />
  )
}
