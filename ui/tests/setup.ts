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

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
  resetPromptStore()
})
afterAll(() => server.close())
