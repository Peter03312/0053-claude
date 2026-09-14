export interface Pt {
  x: number
  y: number
}

export interface Rect {
  x: number
  y: number
  w: number
  h: number
}

export interface BubbleSpec {
  id: string
  x: number
  y: number
  w: number
  h: number
  tail: Pt
  anchor: Pt
  locked: boolean
}

export interface Spec {
  safeArea: Rect
  gap: number
  maxStep: number
  protections: Rect[]
  bubbles: BubbleSpec[]
  order: string[]
}

export interface OrderEdge {
  from: string
  to: string
}

export interface SolveOk {
  status: 'ok'
  movedCount: number
  totalDisplacement: number
  maxDisplacement: number
  positions: Record<string, Pt>
  edges: OrderEdge[]
}

export interface SolveFail {
  status: 'no_solution'
  message: string
  conflicts: { pair: [string, string] }[]
  emptyDomains: string[]
}

export type SolveResult = SolveOk | SolveFail

export interface ProjectInfo {
  id: number
  name: string
  created_at: string
  versions: number
  updated_at: string | null
}

export interface VersionInfo {
  version_no: number
  created_at: string
}
