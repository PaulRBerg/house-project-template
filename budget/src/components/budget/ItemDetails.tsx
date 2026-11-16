import { ExternalLink } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";

import {
  beneficiaryName,
  beneficiaryNamesById,
  type BudgetDocument,
  type BudgetSource,
  type DerivedItem,
} from "../../domain/index.js";
import {
  formatBpsPercent,
  formatCount,
  formatDate,
  formatDateRange,
  formatMoney,
} from "../../ui/format.js";
import { Dialog } from "../shared/Dialog.js";
import { ItemBrandIcon, ItemIcon } from "../shared/ItemIcon.js";
import { PaymentProgress } from "../shared/PaymentProgress.js";
import { accentLinkStyles, cn, definitionListStyles, eyebrowStyles } from "../shared/styles.js";

interface ItemDetailsProps {
  document: BudgetDocument;
  entry: DerivedItem;
  open: boolean;
  onClose: () => void;
  onExited: () => void;
}

const taxLabels = {
  included: "inclus",
  excluded: "exclus",
  "not-applicable": "neaplicabil",
  unknown: "necunoscut",
};
const confidenceLabels = { high: "ridicată", medium: "medie", low: "scăzută" };

const sectionTitleStyles = cn(eyebrowStyles, "mb-0");
const headlineAmountStyles = "mt-1 text-[1.7rem]/none font-[660] tracking-[-0.03em] tabular-nums";

const noteMarkdownComponents = {
  a({ children, node: _node, ...props }) {
    return (
      <a
        {...props}
        className="text-accent underline underline-offset-3"
        rel="noreferrer"
        target="_blank"
      >
        {children}
      </a>
    );
  },
} satisfies Components;

function formatEuroText(text: string): string {
  return text.replace(/\bEUR\b/g, "€");
}

function SourceReference({ source }: { source: BudgetSource }) {
  return (
    <article className="py-3.5">
      <a
        className={cn(accentLinkStyles, "items-start")}
        href={source.url}
        rel="noreferrer"
        target="_blank"
      >
        {source.title}
        <ExternalLink className="mt-1 flex-none" aria-hidden="true" size={13} />
      </a>
      <p className="mt-1.5 whitespace-pre-line">{formatEuroText(source.scope)}</p>
      <p className="mt-2 text-[0.7rem] text-muted">
        Accesată {formatDate(source.accessedOn)} · încredere {confidenceLabels[source.confidence]} ·
        TVA {taxLabels[source.tax.status]}
        {source.tax.rateBps !== undefined && ` (${formatBpsPercent(source.tax.rateBps)})`}
      </p>
      {source.provenance && (
        <div className="mt-1 text-[0.7rem] text-muted">
          <p>Moneda sursei: {source.provenance.currency}</p>
          {source.provenance.note && (
            <p className="mt-1 whitespace-pre-line">{formatEuroText(source.provenance.note)}</p>
          )}
        </div>
      )}
    </article>
  );
}

function ItemContext({ document, entry }: Pick<ItemDetailsProps, "document" | "entry">) {
  const { item } = entry;
  const group = document.groups.find((candidate) => candidate.id === item.groupId);
  const milestone = document.milestones.find((candidate) => candidate.id === item.milestoneId);
  const payee = beneficiaryName(item, beneficiaryNamesById(document.beneficiaries));

  return (
    <section className="mt-7 border-t border-line pt-5" aria-labelledby="item-context-title">
      <h3 className={sectionTitleStyles} id="item-context-title">
        Context
      </h3>
      <dl className={cn(definitionListStyles, "mt-3")}>
        <dt>Categorie</dt>
        <dd>{group?.label}</dd>
        <dt>Etapă</dt>
        <dd>{milestone?.label}</dd>
        <dt>Tip de cost</dt>
        <dd>{item.costScope === "core" ? "Buget de bază" : "Bun mobil"}</dd>
        <dt>Plăți</dt>
        <dd className="flex flex-wrap items-center gap-x-2">
          {entry.totalCents > 0 ? (
            <PaymentProgress
              label={item.label}
              settledCents={entry.settledCents}
              totalCents={entry.totalCents}
            />
          ) : (
            "Fără cost"
          )}
          {item.completion.completedOn && `· ${formatDate(item.completion.completedOn)}`}
        </dd>
        <dt>În buget</dt>
        <dd>{entry.effectivelyArchived ? "Arhivat" : item.included ? "Inclus" : "Neinclus"}</dd>
        <dt>Calendar</dt>
        <dd>
          {formatDateRange(entry.scheduleStartOn, entry.scheduleFinalOn) || formatDate(undefined)}
        </dd>
        <dt>Beneficiar</dt>
        <dd>{payee}</dd>
        {item.brand && (
          <>
            <dt>Marcă</dt>
            <dd>{item.brand}</dd>
          </>
        )}
      </dl>
      {item.briefReferences.length > 0 && (
        <div className="mt-5">
          <h4 className="text-[0.72rem] font-bold text-muted">Referințe din brief</h4>
          <ul className="mt-2 flex list-none flex-wrap gap-1.5 p-0">
            {item.briefReferences.map((reference) => (
              <li
                className="rounded-full border border-line bg-canvas px-2.5 py-1 text-[0.7rem] font-medium"
                key={reference.recordId}
              >
                {reference.recordId}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function ItemDetails({ document, entry, open, onClose, onExited }: ItemDetailsProps) {
  const { item } = entry;
  const { estimate } = item;
  const sources = document.sources.filter((source) => item.sourceIds.includes(source.id));
  const owned = item.ownership === "owned";
  const showForecast = entry.active && !owned;

  return (
    <Dialog
      eyebrow="Detalii cost"
      leading={
        <span
          aria-hidden="true"
          className="inline-flex size-11 flex-none items-center justify-center rounded-[10px] border border-stage/16 bg-stage-tint [&>svg]:text-stage"
          data-stage={item.milestoneId}
        >
          <ItemIcon itemId={item.id} size={22} />
        </span>
      }
      onExited={onExited}
      onRequestClose={onClose}
      open={open}
      title={item.label}
    >
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5 text-[0.8rem] leading-relaxed">
        <section aria-label="Baza estimării">
          <div
            className={cn(
              "grid gap-5 border-y border-line py-4 [&>div+div]:border-l [&>div+div]:border-line [&>div+div]:pl-5",
              showForecast && "grid-cols-2",
            )}
          >
            <div>
              <p className="flex items-center gap-1.5 text-[0.7rem] text-muted">
                {owned
                  ? estimate.fixed
                    ? "Preț istoric"
                    : "Valoare istorică estimată"
                  : "Estimare de bază"}
                <ItemBrandIcon itemId={item.id} size={13} />
              </p>
              <p className={headlineAmountStyles}>{formatMoney(entry.estimateCents)}</p>
              {estimate.kind === "quantity-rate" && (
                <p className="mt-2 tabular-nums">
                  {estimate.quantity} {estimate.unit} ×{" "}
                  {formatMoney(estimate.rates.baseCents, true)}/{estimate.unit}
                  {estimate.quantityBasis === "built-area" && " · aria construită desfășurată"}
                </p>
              )}
              <p className="mt-1 text-[0.7rem] text-muted">
                Estimat la {formatDate(estimate.pricedOn)} ·{" "}
                {estimate.fixed ? "Preț fix" : "Estimare ajustabilă"}
              </p>
            </div>
            {showForecast && (
              <div>
                <p className="text-[0.7rem] text-muted">Prognoză</p>
                <p className={headlineAmountStyles}>{formatMoney(entry.forecastCents)}</p>
                <p className="mt-2 text-[0.7rem] text-muted">
                  {entry.contingencyCents > 0
                    ? `Include rezerva de ${formatMoney(entry.contingencyCents)}.`
                    : "Fără rezervă de risc."}
                </p>
              </div>
            )}
          </div>
          {item.notes && (
            <div className="mt-4 space-y-3 [&_li]:pl-1 [&_ol]:list-decimal [&_ol]:space-y-1.5 [&_ol]:pl-5 [&_p]:leading-relaxed [&_strong]:font-bold [&_ul]:list-disc [&_ul]:space-y-1.5 [&_ul]:pl-5">
              <ReactMarkdown components={noteMarkdownComponents} skipHtml>
                {item.notes}
              </ReactMarkdown>
            </div>
          )}
        </section>

        <section className="mt-7 border-t border-line pt-5" aria-labelledby="item-sources-title">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className={sectionTitleStyles} id="item-sources-title">
              Surse de preț
            </h3>
            {sources.length > 0 && (
              <span className="text-[0.7rem] text-muted tabular-nums">
                {formatCount(sources.length, { one: "sursă", other: "surse" })}
              </span>
            )}
          </div>
          {sources.length > 0 ? (
            <div className="mt-1 divide-y divide-line">
              {sources.map((source) => (
                <SourceReference key={source.id} source={source} />
              ))}
            </div>
          ) : (
            <p className="mt-3 text-muted">Nu există o sursă externă atașată acestui reper.</p>
          )}
        </section>

        <ItemContext document={document} entry={entry} />
      </div>
    </Dialog>
  );
}
