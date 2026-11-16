import { Compass, ShieldCheck } from "lucide-react";

import { CONTINGENCY_BPS } from "../../domain/index.js";
import { formatBpsPercent } from "../../ui/format.js";
import { Dialog } from "../shared/Dialog.js";
import { iconLabelStyles } from "../shared/styles.js";

interface AssumptionsDialogProps {
  open: boolean;
  onClose: () => void;
  onExited: () => void;
}

export function AssumptionsDialog(props: AssumptionsDialogProps) {
  return (
    <Dialog
      eyebrow="Model financiar"
      onExited={props.onExited}
      onRequestClose={props.onClose}
      open={props.open}
      title="Ipoteze de calcul"
    >
      <div className="p-6">
        <p className="text-[0.83rem] leading-relaxed text-muted">
          Prețurile sunt estimate în 2026, la valorile curente, fără creștere anuală. Prognoza
          adaugă doar rezerva de risc costurilor viitoare eligibile.
        </p>
        <div className="mt-5.5">
          <p className="mb-5.5 text-[0.83rem] leading-relaxed text-muted">
            „Rămas de plată” și fluxul implicit acoperă etapele până la mutare, în iunie 2029. Extra
            are buget separat pentru iunie 2029 – iunie 2031; costurile sale se consultă în tabul
            Extra sau selectând această etapă în Flux. Lista beneficiarilor include toate etapele.
          </p>
          <p className={iconLabelStyles}>
            <ShieldCheck aria-hidden="true" size={16} /> Rezervă de risc
          </p>
          <p className="mt-1.5 text-[1.4rem] font-bold" data-testid="contingency-rate">
            {formatBpsPercent(CONTINGENCY_BPS)}
          </p>
          <p className="mt-1 text-[0.64rem] font-medium text-muted">
            Fixă. Se aplică numai costurilor viitoare ale casei, nu terenului, bunurilor mobile,
            plăților efectuate sau bunurilor deja deținute. Se afișează separat; nu este o obligație
            cu termen.
          </p>
        </div>
        <div className="mt-6 flex gap-3 border-t border-line pt-5">
          <Compass className="mt-0.5 flex-none text-accent" aria-hidden="true" size={20} />
          <div className="text-[0.8rem]">
            <strong className="font-bold">Bugetul este încă de stabilit</strong>
            <p className="mt-1 text-[0.76rem] text-muted">
              Explorează intervalele de cost pe măsură ce conturezi casa. Estimările și calendarul
              plăților se actualizează odată cu alegerile tale.
            </p>
          </div>
        </div>
      </div>
    </Dialog>
  );
}
