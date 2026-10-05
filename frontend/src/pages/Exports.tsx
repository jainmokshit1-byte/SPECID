import { useMutation } from "@tanstack/react-query";
import { FileJson, FileSpreadsheet, PackageOpen } from "lucide-react";
import { useState } from "react";
import { download } from "../api/registry";
import { useUser } from "../auth/useAuth";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { INPUT, ProblemAlert } from "../components/ui/Form";
import { PageHeader } from "../components/ui/PageHeader";

const CPSES = ["CPSE-A", "CPSE-B", "CPSE-C"];

/** S8c Exports (App Flow 5.8): the crosswalk in three formats and the migration pack per CPSE.
 * Every download writes an audit event. */
export function Exports() {
  const user = useUser();
  const own = user.role === "MAKER" || user.role === "CHECKER";
  const [cpse, setCpse] = useState(user.cpse_code ?? "CPSE-A");
  const dl = useMutation({ mutationFn: ([path, name]: [string, string]) => download(path, name) });
  return (
    <section className="max-w-5xl">
      <PageHeader
        title="Exports"
        purpose="Files for your SAP team: the mapping from old codes to national codes, and what to do with each old code."
      />
      <ProblemAlert error={dl.error} />
      <div className="grid gap-5 md:grid-cols-2">
        <Card
          title="Crosswalk"
          hint="Every legacy code mapped to its national code, with unit and factor."
        >
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              icon={FileSpreadsheet}
              onClick={() => dl.mutate(["/exports/crosswalk?format=csv", "crosswalk.csv"])}
            >
              CSV
            </Button>
            <Button
              variant="secondary"
              icon={FileSpreadsheet}
              onClick={() => dl.mutate(["/exports/crosswalk?format=sap_csv", "sap_crosswalk.csv"])}
            >
              SAP-style CSV
            </Button>
            <Button
              variant="secondary"
              icon={FileJson}
              onClick={() => dl.mutate(["/exports/crosswalk?format=json", "crosswalk.json"])}
            >
              JSON
            </Button>
          </div>
          <p className="mt-3 text-micro text-muted">
            SAP-style columns: MATNR; ZZ_CNMC; MAKTX_NATIONAL; MEINS; UMREZ; MSTAE_RECOMMENDED.
            Confirm the target fields with your SAP team.
          </p>
        </Card>
        <Card
          title="Migration pack"
          hint="Per CPSE: keep, block for new buying, or phase out when stock is zero."
        >
          <div className="flex flex-wrap items-center gap-2">
            <select
              aria-label="CPSE"
              className={`${INPUT} w-36`}
              value={cpse}
              disabled={own}
              onChange={(e) => setCpse(e.target.value)}
            >
              {CPSES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <Button
              icon={PackageOpen}
              busy={dl.isPending}
              onClick={() =>
                dl.mutate([`/exports/migration-pack?cpse=${cpse}`, `migration_pack_${cpse}.csv`])
              }
            >
              Download migration pack
            </Button>
          </div>
          <p className="mt-3 text-micro text-muted">
            Recommendations only: each CPSE applies them through its own master-data process.
            {own ? " You can download your own CPSE's pack." : ""}
          </p>
        </Card>
      </div>
    </section>
  );
}
