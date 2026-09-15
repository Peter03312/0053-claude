import type { BubbleSpec } from './types'

/** 将尾线起点吸附到矩形边界上最近的点（用于宽高变化后保持尾线落在泡边）。 */
export function clampTailToPerimeter(b: BubbleSpec): void {
  const { x, y, w, h } = b
  let tx = Math.min(Math.max(b.tail.x, x), x + w)
  let ty = Math.min(Math.max(b.tail.y, y), y + h)
  if (tx !== x && tx !== x + w && ty !== y && ty !== y + h) {
    // 落在矩形内部：吸附到最近的一条边
    const dl = tx - x
    const dr = x + w - tx
    const dt = ty - y
    const db = y + h - ty
    const m = Math.min(dl, dr, dt, db)
    if (m === dl) tx = x
    else if (m === dr) tx = x + w
    else if (m === dt) ty = y
    else ty = y + h
  }
  b.tail.x = tx
  b.tail.y = ty
}

/**
 * 更新气泡矩形（画布拖拽与数值框共用）：
 * 尾线起点随位置同量平移；宽高变化后把尾线吸附回泡边。
 * 参数非法（非整数、非正宽高）时不做任何修改并返回 false。
 */
export function setBubbleRect(
  b: BubbleSpec,
  x: number,
  y: number,
  w: number,
  h: number,
): boolean {
  if (![x, y, w, h].every(Number.isInteger) || w <= 0 || h <= 0) return false
  const dx = x - b.x
  const dy = y - b.y
  b.x = x
  b.y = y
  b.w = w
  b.h = h
  b.tail.x += dx
  b.tail.y += dy
  clampTailToPerimeter(b)
  return true
}
