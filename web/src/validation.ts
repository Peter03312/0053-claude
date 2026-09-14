import type { BubbleSpec, Rect, Spec } from './types'

function isInt(v: unknown): v is number {
  return typeof v === 'number' && Number.isInteger(v)
}

function rectOk(r: Rect): boolean {
  return isInt(r.x) && isInt(r.y) && isInt(r.w) && isInt(r.h) && r.w > 0 && r.h > 0
}

function onPerimeter(r: Rect, x: number, y: number): boolean {
  const onXEdge = r.x <= x && x <= r.x + r.w && (y === r.y || y === r.y + r.h)
  const onYEdge = r.y <= y && y <= r.y + r.h && (x === r.x || x === r.x + r.w)
  return onXEdge || onYEdge
}

function bubbleRect(b: BubbleSpec): Rect {
  return { x: b.x, y: b.y, w: b.w, h: b.h }
}

/** 与后端一致的客户端校验，返回中文错误列表（空数组 = 合法）。 */
export function validateSpec(spec: Spec): string[] {
  const errors: string[] = []
  if (!rectOk(spec.safeArea)) errors.push('安全区的 x/y/w/h 必须是整数且宽、高为正')
  if (!isInt(spec.gap) || spec.gap < 0) errors.push('阅读间距 gap 必须是非负整数')
  if (!isInt(spec.maxStep) || spec.maxStep < 0 || spec.maxStep > 100)
    errors.push('单泡最大曼哈顿位移 maxStep 必须是 0..100 的整数')

  spec.protections.forEach((p, i) => {
    if (!rectOk(p)) errors.push(`保护框 #${i + 1} 的 x/y/w/h 必须是整数且宽、高为正`)
  })

  const n = spec.bubbles.length
  if (n < 2 || n > 12) errors.push(`对白泡数量必须在 2..12 之间，当前 ${n} 个`)

  const seen = new Set<string>()
  spec.bubbles.forEach((b, i) => {
    const label = b.id ? `气泡「${b.id}」` : `第 ${i + 1} 个气泡`
    if (!b.id || !b.id.trim()) errors.push(`第 ${i + 1} 个气泡编号不能为空`)
    else if (seen.has(b.id)) errors.push(`气泡编号「${b.id}」重复`)
    else seen.add(b.id)
    if (!isInt(b.x) || !isInt(b.y) || !isInt(b.w) || !isInt(b.h) || b.w <= 0 || b.h <= 0)
      errors.push(`${label} 的矩形参数必须是整数且宽、高为正`)
    if (!isInt(b.tail.x) || !isInt(b.tail.y)) errors.push(`${label} 的尾线起点必须是整数坐标`)
    else if (isInt(b.x) && isInt(b.y) && isInt(b.w) && isInt(b.h) && b.w > 0 && b.h > 0) {
      if (!onPerimeter(bubbleRect(b), b.tail.x, b.tail.y))
        errors.push(`${label} 的尾线起点必须落在泡边上`)
    }
    if (!isInt(b.anchor.x) || !isInt(b.anchor.y)) errors.push(`${label} 的角色落点必须是整数坐标`)
  })

  const ids = spec.bubbles.map((b) => b.id)
  const orderSet = new Set(spec.order)
  if (spec.order.length !== ids.length || ids.some((id) => !orderSet.delete(id)))
    errors.push('台词总序必须恰好包含每个气泡编号一次')
  else if (orderSet.size !== 0) errors.push('台词总序必须恰好包含每个气泡编号一次')

  return errors
}
