import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { listRuns } from "../api/runs";

/** The run a run-scoped page shows (App Flow 3.3): `?run=` in the URL, else the newest
 * finished run. */
export function useRun() {
  const [params, setParams] = useSearchParams();
  const runs = useQuery({ queryKey: ["runs"], queryFn: listRuns });
  const done = (runs.data ?? []).filter((r) => r.status === "DONE");
  const run = params.get("run") ?? done[0]?.id ?? null;
  function setRun(id: string) {
    const next = new URLSearchParams(params);
    next.set("run", id);
    setParams(next, { replace: true });
  }
  return { run, done, setRun, loading: runs.isPending };
}
