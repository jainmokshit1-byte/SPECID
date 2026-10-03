import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { clearSession } from "./auth/session";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  clearSession(); // the in-memory token outlives sessionStorage.clear()
  sessionStorage.clear();
  localStorage.clear();
});
