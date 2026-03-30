/* ResizableHandle — Divisoria arrastavel para redimensionar paineis */

import { useCallback, useRef, useEffect } from 'react'

interface ResizableHandleProps {
  onResize: (delta: number) => void
  direction?: 'horizontal' | 'vertical'
}

export default function ResizableHandle({ onResize, direction = 'horizontal' }: ResizableHandleProps) {
  const dragging = useRef(false)
  const lastPos = useRef(0)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragging.current = true
    lastPos.current = direction === 'horizontal' ? e.clientX : e.clientY
    document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize'
    document.body.style.userSelect = 'none'
  }, [direction])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const pos = direction === 'horizontal' ? e.clientX : e.clientY
      const delta = pos - lastPos.current
      if (Math.abs(delta) >= 1) {
        onResize(delta)
        lastPos.current = pos
      }
    }

    const handleMouseUp = () => {
      if (dragging.current) {
        dragging.current = false
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [onResize, direction])

  if (direction === 'vertical') {
    return (
      <div
        onMouseDown={handleMouseDown}
        className="flex-shrink-0 group"
        style={{ height: '5px', cursor: 'row-resize', position: 'relative' }}
      >
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-px transition-all group-hover:h-[3px] group-hover:rounded"
          style={{ background: 'var(--sf-border-subtle)' }}
        />
        <div className="absolute inset-x-0 top-0 h-full opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ background: 'rgba(16,185,129,0.1)' }}
        />
      </div>
    )
  }

  return (
    <div
      onMouseDown={handleMouseDown}
      className="flex-shrink-0 group"
      style={{ width: '5px', cursor: 'col-resize', position: 'relative' }}
    >
      <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-px transition-all group-hover:w-[3px] group-hover:rounded"
        style={{ background: 'var(--sf-border-subtle)' }}
      />
      <div className="absolute inset-y-0 left-0 w-full opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ background: 'rgba(16,185,129,0.1)' }}
      />
    </div>
  )
}
