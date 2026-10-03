import { useQuery } from "@tanstack/react-query";
import { type AirGap, ApiError, type Health, apiGet } from "../api/client";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<Health>("/health"),
    refetchInterval: 30_000,
    retry: false,
  });
}

/** Footer polls /system/airgap every 10 s (03 App Flow 3.3). A 404 means "not built yet". */
export function useAirGap() {
  return useQuery({
    queryKey: ["airgap"],
    queryFn: async (): Promise<AirGap | null> => {
      try {
        return await apiGet<AirGap>("/system/airgap");
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
    refetchInterval: 10_000,
    retry: false,
  });
}
