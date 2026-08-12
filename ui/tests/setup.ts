import "@testing-library/jest-dom"
import { cleanup } from "@testing-library/react"
import { afterAll, afterEach, beforeAll } from "vitest"
import { server } from "./mocks/server"
import { resetPromptStore } from "./mocks/handlers"

// cmdk uses ResizeObserver and scrollIntoView internally; polyfill both for jsdom.
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.HTMLElement.prototype.scrollIntoView = () => {}

// CodeMirror 6 measures text layout via Range.getClientRects/getBoundingClientRect to
// lay out lines; jsdom doesn't implement layout at all, so stub both with empty/zeroed
// results — CM6 tolerates that (it's designed to degrade, not crash, without real layout).
const emptyRectList = () => Object.assign([], { item: () => null }) as unknown as DOMRectList
const zeroRect = () =>
  ({ x: 0, y: 0, width: 0, height: 0, top: 0, left: 0, right: 0, bottom: 0, toJSON() {} }) as DOMRect
Range.prototype.getClientRects = emptyRectList
Range.prototype.getBoundingClientRect = zeroRect
window.HTMLElement.prototype.getClientRects = emptyRectList

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
  resetPromptStore()
})
afterAll(() => server.close())
