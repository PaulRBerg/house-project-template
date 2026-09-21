import { Field } from "@base-ui/react/field";
import { NumberField } from "@base-ui/react/number-field";
import { Compass, ShieldCheck, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import type { BudgetDocument } from "../../domain/index.js";
import { AppButton } from "../shared/AppButton.js";
import { ConfirmDialog } from "../shared/ConfirmDialog.js";
import { Dialog } from "../shared/Dialog.js";
import {
  editorActionsStyles,
  editorFieldsetStyles,
  editorFormStyles,
  fieldStyles,
  iconLabelStyles,
  moneyInputStyles,
} from "../shared/styles.js";

interface AssumptionsEditorProps {
  document: BudgetDocument;
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onExited: () => void;
  onDirtyChange: (dirty: boolean) => void;
  onSave: (document: BudgetDocument) => Promise<boolean>;
}

export function AssumptionsEditor(props: AssumptionsEditorProps) {
  const { onDirtyChange, open } = props;
  const [growth, setGrowth] = useState<number | null>(props.document.project.annualGrowthBps / 100);
  const [reserve, setReserve] = useState<number | null>(
    props.document.project.contingencyBps / 100,
  );
  const [error, setError] = useState<string>();
  const [discardConfirmationOpen, setDiscardConfirmationOpen] = useState(false);

  const dirty = useMemo(
    () =>
      growth === null ||
      reserve === null ||
      Math.round(growth * 100) !== props.document.project.annualGrowthBps ||
      Math.round(reserve * 100) !== props.document.project.contingencyBps,
    [growth, props.document.project, reserve],
  );
  useEffect(() => onDirtyChange(open && dirty), [dirty, onDirtyChange, open]);

  const submit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    if (!open || props.busy) return;
    if (
      growth === null ||
      !Number.isFinite(growth) ||
      growth < 0 ||
      growth > 25 ||
      reserve === null ||
      !Number.isFinite(reserve) ||
      reserve < 0 ||
      reserve > 50
    ) {
      setError("Creșterea trebuie să fie între 0–25%, iar rezerva între 0–50%.");
      return;
    }
    const next: BudgetDocument = {
      ...props.document,
      project: {
        ...props.document.project,
        annualGrowthBps: Math.round(growth * 100),
        contingencyBps: Math.round(reserve * 100),
      },
    };
    if (await props.onSave(next)) props.onClose();
    else {
      setError(
        "Salvarea locală a eșuat. Ipotezele rămân în editor; verifică mesajul aplicației și reîncearcă.",
      );
    }
  };

  const requestClose = (): void => {
    if (!open) return;
    if (dirty) setDiscardConfirmationOpen(true);
    else props.onClose();
  };

  return (
    <>
      <Dialog
        eyebrow="Model financiar"
        onExited={props.onExited}
        onRequestClose={requestClose}
        open={props.open}
        title="Ipoteze de calcul"
      >
        <form className={editorFormStyles} noValidate onSubmit={(event) => void submit(event)}>
          <fieldset className={editorFieldsetStyles} disabled={props.busy || !open}>
            <div className="flex-1 overflow-auto p-6">
              <p className="mb-5.5 text-[0.83rem] leading-relaxed text-muted">
                Creșterea se calculează de la data estimării fiecărui cost și se aplică numai
                sumelor viitoare eligibile, până la termenul fiecărei tranșe.
              </p>
              <div className="mt-3.5 grid grid-cols-2 gap-3.5 **:data-field:mt-0">
                <Field.Root className={fieldStyles} name="annual-growth">
                  <Field.Label className={iconLabelStyles}>
                    <TrendingUp aria-hidden="true" size={16} /> Creștere anuală
                  </Field.Label>
                  <NumberField.Root
                    allowOutOfRange
                    max={25}
                    min={0}
                    name="annual-growth"
                    onValueChange={setGrowth}
                    step={0.1}
                    value={growth}
                  >
                    <NumberField.Group className={moneyInputStyles}>
                      <NumberField.Input />
                      <b>%</b>
                    </NumberField.Group>
                  </NumberField.Root>
                  <Field.Description className="text-[0.64rem] font-medium text-muted">
                    Nu se aplică terenului, prețurilor fixe sau bunurilor deja deținute.
                  </Field.Description>
                </Field.Root>
                <Field.Root className={fieldStyles} name="contingency">
                  <Field.Label className={iconLabelStyles}>
                    <ShieldCheck aria-hidden="true" size={16} /> Rezervă de risc
                  </Field.Label>
                  <NumberField.Root
                    allowOutOfRange
                    max={50}
                    min={0}
                    name="contingency"
                    onValueChange={setReserve}
                    step={0.1}
                    value={reserve}
                  >
                    <NumberField.Group className={moneyInputStyles}>
                      <NumberField.Input />
                      <b>%</b>
                    </NumberField.Group>
                  </NumberField.Root>
                  <Field.Description className="text-[0.64rem] font-medium text-muted">
                    Se afișează separat; nu este o obligație cu termen.
                  </Field.Description>
                </Field.Root>
              </div>
              <div className="mt-6 flex gap-3 border-t border-line pt-5">
                <Compass className="mt-0.5 flex-none text-accent" aria-hidden="true" size={20} />
                <div className="text-[0.8rem]">
                  <strong className="font-bold">Bugetul este încă de stabilit</strong>
                  <p className="mt-1 text-[0.76rem] text-muted">
                    Explorează intervalele de cost pe măsură ce conturezi casa. Estimările și
                    calendarul plăților se actualizează odată cu alegerile tale.
                  </p>
                </div>
              </div>
              {error && (
                <p
                  className="mt-4 rounded-[7px] border border-form-error-line bg-form-error px-3 py-2.75 text-[0.72rem] text-form-error-ink [&_ul]:mt-1.5 [&_ul]:list-disc [&_ul]:pl-4.5"
                  role="alert"
                >
                  {error}
                </p>
              )}
            </div>
            <footer className={editorActionsStyles}>
              <AppButton intent="secondary" onClick={requestClose} type="button">
                Renunță
              </AppButton>
              <AppButton intent="primary" disabled={!open || props.busy || !dirty} type="submit">
                {props.busy ? "Se salvează…" : "Salvează ipotezele"}
              </AppButton>
            </footer>
          </fieldset>
        </form>
      </Dialog>
      <ConfirmDialog
        cancelLabel="Păstrează modificările"
        confirmLabel="Renunță la modificări"
        description="Modificările nesalvate vor fi pierdute."
        onConfirm={() => {
          setDiscardConfirmationOpen(false);
          props.onClose();
        }}
        onOpenChange={setDiscardConfirmationOpen}
        open={discardConfirmationOpen}
        title="Renunți la modificările nesalvate?"
      />
    </>
  );
}
