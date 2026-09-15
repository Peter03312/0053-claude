import { describe, expect, it } from 'vitest'
import { clampTailToPerimeter, setBubbleRect } from './bubbleOps'
import type { BubbleSpec } from './types'

function mk(): BubbleSpec {
  return {
    id: 'A',
    x: 10,
    y: 20,
    w: 90,
    h: 48,
    tail: { x: 55, y: 68 }, // 底边中点
    anchor: { x: 55, y: 124 },
    locked: false,
  }
}

describe('setBubbleRect', () => {
  it('数值框调整位置时尾线起点同量平移，且仍落在泡边上', () => {
    const b = mk()
    expect(setBubbleRect(b, 30, 45, 90, 48)).toBe(true)
    expect(b.tail).toEqual({ x: 75, y: 93 }) // (55+20, 68+25)
    expect(b.tail.y).toBe(b.y + b.h) // 仍在新矩形底边上
    expect(b.anchor).toEqual({ x: 55, y: 124 }) // 角色落点不动
  })

  it('宽高变化后尾线吸附到最近的泡边', () => {
    const b = mk()
    expect(setBubbleRect(b, 10, 20, 30, 48)).toBe(true)
    // 原尾线 (55,68)：x 超出新右边界 40 → 吸附到右边
    expect(b.tail).toEqual({ x: 40, y: 68 })
  })

  it('尾线原本在边上时不会被误改', () => {
    const b = mk()
    clampTailToPerimeter(b)
    expect(b.tail).toEqual({ x: 55, y: 68 })
  })

  it('拒绝非法参数且不产生任何修改', () => {
    const b = mk()
    expect(setBubbleRect(b, 1.5, 20, 90, 48)).toBe(false)
    expect(setBubbleRect(b, 10, 20, 0, 48)).toBe(false)
    expect(setBubbleRect(b, 10, 20, 90, Number.NaN)).toBe(false)
    expect([b.x, b.y, b.w, b.h]).toEqual([10, 20, 90, 48])
    expect(b.tail).toEqual({ x: 55, y: 68 })
  })
})
