import { getApiBaseUrl } from "./api";
import {
  clearPersistedSessionSnapshot,
  hasPersistedSessionSnapshot,
  useAppStore,
} from "./store";

const BACKEND_BOOT_KEY = "wsdfc:backend-boot-id:v1";

interface BootIdResponse {
  boot_id?: string;
}

function safeWindow(): Window | null {
  return typeof window === "undefined" ? null : window;
}

export async function resetIfBackendRestarted(): Promise<boolean> {
  const w = safeWindow();
  if (!w) return false;

  try {
    const res = await fetch(`${getApiBaseUrl()}/session/boot-id`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });

    if (!res.ok) return false;

    const payload = (await res.json()) as BootIdResponse;
    const bootId = payload.boot_id;
    if (!bootId) return false;

    const previousBootId = w.localStorage.getItem(BACKEND_BOOT_KEY);
    const backendChanged = previousBootId !== bootId;

    if (!backendChanged) return false;

    const hadSavedSession = hasPersistedSessionSnapshot();
    w.localStorage.setItem(BACKEND_BOOT_KEY, bootId);

    if (!hadSavedSession) return false;

    clearPersistedSessionSnapshot();
    useAppStore.getState().resetAll();
    return true;
  } catch {
    return false;
  }
}
