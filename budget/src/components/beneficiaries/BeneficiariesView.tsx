import { ArrowLeft, ExternalLink } from "lucide-react";
import { type ReactNode, useMemo } from "react";

import {
  TBD_BENEFICIARY_ID,
  type Beneficiary,
  type BeneficiaryBundle,
  type BudgetDocument,
  type DerivedItem,
} from "../../domain/index.js";
import { formatDateRange, formatItemCost, formatMoney, formatMoneyRange } from "../../ui/format.js";
import { ItemIcon } from "../shared/ItemIcon.js";
import { PaymentProgress } from "../shared/PaymentProgress.js";
import {
  accentLinkStyles,
  cn,
  definitionListStyles,
  emptyStateStyles,
  eyebrowStyles,
  linkButtonStyles,
  moneyCellStyles,
  pageHeadingStyles,
  tableCellStyles,
  tableHeaderStyles,
  tableScrollerStyles,
} from "../shared/styles.js";

interface BeneficiariesViewProps {
  bundles: BeneficiaryBundle[];
  document: BudgetDocument;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onOpenItem: (itemId: string) => void;
}

const contactLinkStyles = cn(accentLinkStyles, "items-center");

const nameButtonStyles = cn(linkButtonStyles, "text-[0.84rem] font-[680]");

function contactHostname(website: string): string {
  try {
    return new URL(website).hostname;
  } catch {
    return website;
  }
}

function ContactLinks({
  beneficiary,
  fallback,
}: {
  beneficiary: Beneficiary | undefined;
  fallback: ReactNode;
}) {
  if (!beneficiary?.phone && !beneficiary?.email && !beneficiary?.website) return fallback;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      {beneficiary.phone && (
        <a className={contactLinkStyles} href={`tel:${beneficiary.phone}`}>
          {beneficiary.phone}
        </a>
      )}
      {beneficiary.email && (
        <a className={contactLinkStyles} href={`mailto:${beneficiary.email}`}>
          {beneficiary.email}
        </a>
      )}
      {beneficiary.website && (
        <a
          className={contactLinkStyles}
          href={beneficiary.website}
          rel="noreferrer"
          target="_blank"
        >
          {contactHostname(beneficiary.website)}
          <ExternalLink aria-hidden="true" size={13} />
        </a>
      )}
    </div>
  );
}

function BeneficiaryList({
  bundles,
  onSelect,
}: {
  bundles: BeneficiaryBundle[];
  onSelect: (id: string) => void;
}) {
  return (
    <section aria-labelledby="beneficiaries-title" className="max-w-full">
      <p className={eyebrowStyles}>Plăți către beneficiari</p>
      <h1 className={pageHeadingStyles} id="beneficiaries-title">
        Beneficiari
      </h1>
      <p className="mt-2.5 max-w-160 text-[0.9rem] text-muted">
        Cine încasează fiecare element de cost; elementele fără beneficiar cunoscut apar la «TBD».
      </p>
      {bundles.length === 0 ? (
        <p className="mt-7 text-muted">Nu există beneficiari sau elemente de cost.</p>
      ) : (
        <div
          aria-label="Tabel de beneficiari derulabil pe orizontală"
          role="region"
          className={cn(tableScrollerStyles, "mt-5")}
          tabIndex={0}
        >
          <table className="w-full min-w-190 table-fixed border-collapse">
            <thead>
              <tr>
                <th className={tableHeaderStyles}>Beneficiar</th>
                <th className={cn(tableHeaderStyles, "w-[26%]")}>Contact</th>
                <th className={cn(tableHeaderStyles, "w-[10%] text-right")}>Elemente</th>
                <th className={cn(tableHeaderStyles, "w-[16%] text-right")}>Cost</th>
                <th className={cn(tableHeaderStyles, "w-[20%]")}>Plăți</th>
              </tr>
            </thead>
            <tbody>
              {bundles.map((bundle) => (
                <tr className="border-t border-line" key={bundle.id}>
                  <th className={cn(tableCellStyles, "font-normal")} scope="row">
                    <button
                      className={cn(
                        nameButtonStyles,
                        bundle.id === TBD_BENEFICIARY_ID && "text-muted",
                      )}
                      onClick={() => onSelect(bundle.id)}
                      type="button"
                    >
                      {bundle.name}
                    </button>
                  </th>
                  <td className={tableCellStyles}>
                    <ContactLinks
                      beneficiary={bundle.beneficiary}
                      fallback={<span className="text-muted">—</span>}
                    />
                  </td>
                  <td className={cn(tableCellStyles, "text-right tabular-nums")}>
                    {bundle.itemCount}
                  </td>
                  <td className={cn(tableCellStyles, moneyCellStyles, "text-right")}>
                    <strong>{formatMoneyRange(bundle.estimateCents, bundle.totalCents)}</strong>
                  </td>
                  <td className={tableCellStyles}>
                    <PaymentProgress
                      label={bundle.name}
                      settledCents={bundle.settledCents}
                      totalCents={bundle.totalCents}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function BeneficiaryItemRow({
  groupLabels,
  entry,
  onOpenItem,
}: {
  groupLabels: ReadonlyMap<string, string>;
  entry: DerivedItem;
  onOpenItem: (itemId: string) => void;
}) {
  return (
    <tr className={cn("border-t border-line", entry.effectivelyArchived && "opacity-58")}>
      <th className={cn(tableCellStyles, "font-normal")} scope="row">
        <div className="flex items-center gap-2">
          <ItemIcon itemId={entry.item.id} size={16} />
          <button
            aria-haspopup="dialog"
            className={nameButtonStyles}
            onClick={() => onOpenItem(entry.item.id)}
            type="button"
          >
            {entry.item.label}
          </button>
        </div>
      </th>
      <td className={cn(tableCellStyles, "text-[0.78rem] text-muted")}>
        {groupLabels.get(entry.item.groupId)}
      </td>
      <td className={cn(tableCellStyles, moneyCellStyles, "text-right")}>
        <strong>{formatItemCost(entry)}</strong>
      </td>
      <td className={tableCellStyles}>
        {entry.item.paymentMode === "partial-progress" && (
          <PaymentProgress
            label={entry.item.label}
            settledCents={entry.settledCents}
            totalCents={entry.totalCents}
          />
        )}
      </td>
      <td className={cn(tableCellStyles, "text-[0.72rem]")}>
        {formatDateRange(entry.scheduleStartOn, entry.scheduleFinalOn)}
      </td>
    </tr>
  );
}

function BeneficiaryDetail({
  bundle,
  document,
  onBack,
  onOpenItem,
}: {
  bundle: BeneficiaryBundle;
  document: BudgetDocument;
  onBack: () => void;
  onOpenItem: (itemId: string) => void;
}) {
  const isTbd = bundle.id === TBD_BENEFICIARY_ID;
  const groupLabels = useMemo(
    () => new Map(document.groups.map((group) => [group.id, group.label])),
    [document.groups],
  );
  return (
    <section aria-labelledby="beneficiary-detail-title" className="max-w-full">
      <button
        className="inline-flex items-center gap-1.5 border-0 bg-transparent p-0 text-[0.78rem] font-[680] text-muted hover:text-ink"
        onClick={onBack}
        type="button"
      >
        <ArrowLeft aria-hidden="true" size={16} /> Toți beneficiarii
      </button>
      <h1 className={cn(pageHeadingStyles, "mt-3")} id="beneficiary-detail-title">
        {bundle.name}
      </h1>
      <div className="mt-2.5 text-[0.9rem] text-muted">
        {isTbd ? (
          <p>Elemente fără beneficiar stabilit încă.</p>
        ) : (
          <ContactLinks beneficiary={bundle.beneficiary} fallback={<p>Fără date de contact.</p>} />
        )}
      </div>
      <dl className={cn(definitionListStyles, "mt-5 border-t border-line pt-4")}>
        <dt>Elemente</dt>
        <dd className="tabular-nums">{bundle.itemCount}</dd>
        <dt>Cost</dt>
        <dd>{formatMoneyRange(bundle.estimateCents, bundle.totalCents)}</dd>
        <dt>Plătit</dt>
        <dd>{formatMoney(bundle.settledCents)}</dd>
      </dl>
      <div
        aria-label="Tabel de elemente derulabil pe orizontală"
        role="region"
        className={cn(tableScrollerStyles, "mt-5")}
        tabIndex={0}
      >
        <table className="w-full min-w-225 table-fixed border-collapse">
          <thead>
            <tr>
              <th className={tableHeaderStyles}>Element</th>
              <th className={cn(tableHeaderStyles, "w-[24%]")}>Categorie</th>
              <th className={cn(tableHeaderStyles, "w-[16%] text-right")}>Cost</th>
              <th className={cn(tableHeaderStyles, "w-[18%]")}>Plăți</th>
              <th className={cn(tableHeaderStyles, "w-[16%]")}>Calendar</th>
            </tr>
          </thead>
          <tbody>
            {bundle.items.length === 0 ? (
              <tr className="border-t border-line">
                <td className={emptyStateStyles} colSpan={5}>
                  Niciun element atribuit.
                </td>
              </tr>
            ) : (
              bundle.items.map((entry) => (
                <BeneficiaryItemRow
                  entry={entry}
                  groupLabels={groupLabels}
                  key={entry.item.id}
                  onOpenItem={onOpenItem}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function BeneficiariesView({
  bundles,
  document,
  onOpenItem,
  onSelect,
  selectedId,
}: BeneficiariesViewProps) {
  const selected = bundles.find((bundle) => bundle.id === selectedId);
  if (selected) {
    return (
      <BeneficiaryDetail
        bundle={selected}
        document={document}
        onBack={() => onSelect(null)}
        onOpenItem={onOpenItem}
      />
    );
  }
  return <BeneficiaryList bundles={bundles} onSelect={onSelect} />;
}
