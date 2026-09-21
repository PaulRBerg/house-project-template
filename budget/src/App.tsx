import { Tabs } from "@base-ui/react/tabs";
import { CircleAlert, Download, House, Landmark, RotateCcw, WalletCards } from "lucide-react";
import { parseAsString, parseAsStringLiteral, useQueryState } from "nuqs";
import { useEffect, useMemo, useState } from "react";

import { AssumptionsEditor } from "./components/budget/AssumptionsEditor.js";
import { BudgetTable, type BudgetGrouping } from "./components/budget/BudgetTable.js";
import {
  BudgetToolbar,
  type ScopeFilter,
  type StatusFilter,
} from "./components/budget/BudgetToolbar.js";
import { ItemDetails } from "./components/budget/ItemDetails.js";
import { ProjectOverview, StageStrip } from "./components/budget/ProjectOverview.js";
import { CashFlowView } from "./components/planning/index.js";
import { AnimatedView } from "./components/shared/AnimatedView.js";
import { AppButton } from "./components/shared/AppButton.js";
import { AppSelect } from "./components/shared/AppSelect.js";
import { ConfirmDialog } from "./components/shared/ConfirmDialog.js";
import { cn, fieldStyles } from "./components/shared/styles.js";
import { selectBudgetView, type Milestone } from "./domain/index.js";
import { useBudgetStore } from "./hooks/useBudgetStore.js";
import { useExchangeRate, type UseExchangeRateResult } from "./hooks/useExchangeRate.js";
import { downloadBudgetJson } from "./ui/export.js";
import { localCalendarDate } from "./ui/format.js";

type AppView = "budget" | "flux";

function supportsRoomGrouping(categoryId: string): boolean {
  return categoryId === "finish" || categoryId === "move";
}

const NAVIGATION: Array<{ id: AppView; label: string; icon: typeof Landmark }> = [
  { id: "budget", label: "Buget", icon: Landmark },
  { id: "flux", label: "Flux", icon: WalletCards },
];

const BNR_EXCHANGE_RATE_PAGE_URL = "https://www.bnr.ro/541-cursul-de-schimb";

interface ExchangeRateHeaderDisplay {
  text: string;
  title: string | undefined;
  href: string;
}

function formatExchangeRateHeader(exchangeRate: UseExchangeRateResult): ExchangeRateHeaderDisplay {
  const { rate } = exchangeRate;
  if (exchangeRate.status !== "ready" || !rate) {
    return {
      text: exchangeRate.status === "error" ? "Curs indisponibil" : "€1 = … RON",
      title: undefined,
      href: BNR_EXCHANGE_RATE_PAGE_URL,
    };
  }
  const sourceName = rate.source === "ECB" ? "BCE" : "BNR";
  return {
    text: `€1 = ${rate.ronPerEur.toFixed(4)} RON`,
    title: `Curs de referință ${sourceName} din ${rate.rateDate}${rate.stale ? " (cache expirat)" : ""}`,
    href: rate.sourceUrl,
  };
}

export function App() {
  const store = useBudgetStore();
  const exchangeRate = useExchangeRate();
  const exchangeRateHeader = formatExchangeRateHeader(exchangeRate);
  const [activeView, setActiveView] = useQueryState(
    "page",
    parseAsStringLiteral(["budget", "flux"]).withDefault("budget").withOptions({ history: "push" }),
  );
  const [category, setCategory] = useQueryState(
    "category",
    parseAsString.withDefault("construction").withOptions({ history: "push" }),
  );
  const [grouping, setGrouping] = useQueryState(
    "grouping",
    parseAsStringLiteral(["rooms", "categories"] satisfies BudgetGrouping[])
      .withDefault("rooms")
      .withOptions({ history: "push" }),
  );
  const [planningMilestone, setPlanningMilestone] = useState<Milestone["id"] | "all">("all");
  const [search, setSearch] = useState("");
  const [scope, setScope] = useState<ScopeFilter>("all");
  const [status, setStatus] = useState<StatusFilter>("active");
  const [assumptionsEditor, setAssumptionsEditor] = useState(false);
  const [assumptionsOpen, setAssumptionsOpen] = useState(false);
  const [assumptionsDirty, setAssumptionsDirty] = useState(false);
  const [conflictConfirmationOpen, setConflictConfirmationOpen] = useState(false);
  const [itemDetailsId, setItemDetailsId] = useState<string | null>(null);
  const [itemDetailsOpen, setItemDetailsOpen] = useState(false);
  const document = store.document;
  const view = useMemo(
    () =>
      document
        ? selectBudgetView(document, { scenario: "base", asOf: localCalendarDate() })
        : undefined,
    [document],
  );
  const dirty = assumptionsDirty || Boolean(store.unsavedDocument);

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent): void => {
      if (!dirty) return;
      event.preventDefault();
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, [dirty]);

  if (store.loadState === "loading") {
    return (
      <main
        className="flex min-h-screen flex-col items-center justify-center p-7.5 text-center [&_h1]:mt-3 [&_h1]:text-[2rem] [&_h1]:tracking-[-0.04em]"
        aria-busy="true"
      >
        <House className="text-accent" aria-hidden="true" size={28} />
        <h1>House budget</h1>
        <p className="mt-1.5 mb-4.5 max-w-150 text-muted">Se încarcă bugetul local…</p>
      </main>
    );
  }

  if (store.loadState === "error" || !document || !view) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-7.5 text-center [&_h1]:mt-3 [&_h1]:text-[2rem] [&_h1]:tracking-[-0.04em]">
        <CircleAlert className="text-accent" aria-hidden="true" size={28} />
        <h1>Bugetul local nu poate fi deschis</h1>
        <p className="mt-1.5 mb-4.5 max-w-150 text-muted" role="alert">
          {store.loadError ?? "Serverul nu a returnat un document valid."}
        </p>
        <AppButton intent="primary" onClick={() => void store.reload()} type="button">
          <RotateCcw className="text-accent" aria-hidden="true" size={16} /> Reîncearcă
        </AppButton>
      </main>
    );
  }

  const requestAssumptionsEditor = (): void => {
    setAssumptionsEditor(true);
    setAssumptionsOpen(true);
  };
  const requestItemDetails = (id: string): void => {
    setItemDetailsId(id);
    setItemDetailsOpen(true);
  };
  const selectedItem = view.items.find((entry) => entry.item.id === itemDetailsId);
  const selectedCategory =
    view.hierarchy.find((group) => group.id === category)?.id ?? view.hierarchy[0]?.id ?? null;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-(--z-header) grid min-h-14 grid-cols-[minmax(180px,1fr)_auto_minmax(180px,1fr)] items-center gap-7 border-b border-line/82 bg-canvas/92 px-gutter backdrop-blur-[14px]">
        <a
          className="inline-flex items-center gap-2.25 justify-self-start text-[0.88rem] font-[760] no-underline"
          href="#main-content"
          aria-label="House budget, mergi la conținut"
        >
          <House className="text-accent" aria-hidden="true" size={19} />
          <span>House budget</span>
        </a>
        <nav className="flex gap-1 self-stretch" aria-label="Secțiuni principale">
          {NAVIGATION.map(({ id, label, icon: Icon }) => (
            <button
              className="inline-flex items-center gap-1.75 border-0 border-b-2 border-transparent bg-transparent px-3.75 text-[0.79rem] font-bold text-muted hover:text-ink aria-[current=page]:border-accent aria-[current=page]:text-ink [&[aria-current=page]_svg]:text-accent"
              aria-current={activeView === id ? "page" : undefined}
              key={id}
              onClick={() => void setActiveView(id)}
              type="button"
            >
              <Icon aria-hidden="true" size={16} /> {label}
            </button>
          ))}
        </nav>
        <a
          className="justify-self-end text-right text-[0.73rem] font-[650] text-muted no-underline hover:text-ink hover:underline hover:underline-offset-3"
          href={exchangeRateHeader.href}
          rel="noreferrer"
          target="_blank"
          title={exchangeRateHeader.title}
        >
          {exchangeRateHeader.text}
        </a>
      </header>

      {store.saveState === "error" && (
        <aside
          className="relative z-(--z-banner) flex items-center justify-between gap-5 border-b border-error-line bg-error px-gutter py-3 [&>div:first-child]:flex [&>div:first-child]:flex-col"
          role="alert"
        >
          <div>
            <strong className="text-[0.79rem]">Modificarea nu a fost scrisă pe disc.</strong>
            <span className="text-[0.72rem] text-muted">{store.saveError}</span>
          </div>
          <AppButton
            intent="secondary"
            disabled={store.busy}
            onClick={() => void store.retry()}
            type="button"
          >
            Reîncearcă salvarea
          </AppButton>
        </aside>
      )}
      {store.saveState === "conflict" && store.conflict && (
        <aside
          className="relative z-(--z-banner) flex items-center justify-between gap-5 border-b border-notice-line bg-notice px-gutter py-3 [&>div:first-child]:flex [&>div:first-child]:flex-col"
          role="alert"
        >
          <div>
            <strong className="text-[0.79rem]">Bugetul a fost modificat de altă sesiune.</strong>
            <span className="text-[0.72rem] text-muted">
              Draftul tău este păstrat aici. Descarcă-l înainte de a încărca versiunea nouă de pe
              disc.
            </span>
          </div>
          <div className="flex gap-2">
            <AppButton
              intent="secondary"
              onClick={() =>
                store.unsavedDocument &&
                downloadBudgetJson(store.unsavedDocument, "buget-draft-nesalvat.json")
              }
              type="button"
            >
              <Download aria-hidden="true" size={15} /> Descarcă draftul
            </AppButton>
            <AppButton
              intent="primary"
              onClick={() => setConflictConfirmationOpen(true)}
              type="button"
            >
              Încarcă versiunea de pe disc
            </AppButton>
          </div>
        </aside>
      )}

      <main className="mx-auto max-w-385 px-gutter pt-8 pb-20" id="main-content">
        <AnimatedView value={activeView}>
          {(displayedView) => (
            <>
              {displayedView === "budget" ? (
                <Tabs.Root
                  onValueChange={(id) => {
                    if (typeof id !== "string") return;
                    void setCategory(id);
                    if (!supportsRoomGrouping(id)) void setGrouping("rooms");
                  }}
                  value={selectedCategory}
                >
                  <ProjectOverview view={view} project={document.project} />
                  <StageStrip view={view} />
                  <BudgetToolbar
                    disabled={store.busy}
                    onOpenAssumptions={requestAssumptionsEditor}
                    onScopeChange={setScope}
                    onSearchChange={setSearch}
                    onStatusChange={setStatus}
                    scope={scope}
                    search={search}
                    status={status}
                  />
                  {document.items.length === 0 ? (
                    <section className="mt-10 rounded-xl border border-line bg-surface px-5 py-13 text-center text-muted [&_h2]:text-ink">
                      <h2>Bugetul nu conține încă elemente</h2>
                      <p className="mx-auto mt-2 max-w-155">
                        Documentul local a fost încărcat corect. Nu există costuri sau plăți de
                        afișat.
                      </p>
                    </section>
                  ) : (
                    <Tabs.Panel keepMounted value={selectedCategory}>
                      <BudgetTable
                        filters={{ search, scope, status }}
                        grouping={grouping}
                        hierarchy={view.hierarchy}
                        onGroupingChange={(nextGrouping) => void setGrouping(nextGrouping)}
                        onOpenItem={requestItemDetails}
                        selectedCategory={selectedCategory ?? ""}
                      />
                    </Tabs.Panel>
                  )}
                </Tabs.Root>
              ) : (
                <>
                  <section
                    className="flex items-center justify-end gap-2.5"
                    aria-label="Controale planificare"
                  >
                    <div className={cn(fieldStyles, "flex-row! items-center!")}>
                      <span>Etapă</span>
                      <AppSelect
                        className="min-w-52 flex-1 text-[0.82rem] font-medium"
                        label="Etapă"
                        name="planning-milestone"
                        onValueChange={setPlanningMilestone}
                        options={[
                          { value: "all", label: "Toate etapele" },
                          ...document.milestones.map((entry) => ({
                            value: entry.id,
                            label: entry.label,
                          })),
                        ]}
                        value={planningMilestone}
                      />
                    </div>
                    <AppButton
                      intent="secondary"
                      disabled={store.busy}
                      onClick={requestAssumptionsEditor}
                      type="button"
                    >
                      Ipoteze
                    </AppButton>
                  </section>
                  <div className="mt-7">
                    <CashFlowView
                      document={document}
                      milestoneId={planningMilestone}
                      onOpenItem={requestItemDetails}
                      view={view}
                    />
                  </div>
                </>
              )}
            </>
          )}
        </AnimatedView>
        <footer className="mt-13 border-t border-line pt-4 text-[0.68rem] text-muted">
          Datele și sumele sunt estimări de planificare, nu termene garantate sau oferte de preț.
          Validarea proiectului, conformității și costului revine profesioniștilor responsabili.
        </footer>
      </main>

      {selectedItem && (
        <ItemDetails
          document={document}
          entry={selectedItem}
          onClose={() => setItemDetailsOpen(false)}
          onExited={() => setItemDetailsId(null)}
          open={itemDetailsOpen}
        />
      )}

      {assumptionsEditor && (
        <AssumptionsEditor
          busy={store.busy}
          document={document}
          onClose={() => {
            setAssumptionsOpen(false);
          }}
          onExited={() => {
            setAssumptionsEditor(false);
            setAssumptionsDirty(false);
          }}
          onDirtyChange={setAssumptionsDirty}
          onSave={store.persist}
          open={assumptionsOpen}
        />
      )}
      <ConfirmDialog
        cancelLabel="Păstrează draftul"
        confirmLabel="Încarcă versiunea de pe disc"
        description="Draftul nesalvat din aplicație va fi înlocuit cu versiunea curentă de pe disc."
        onConfirm={() => {
          setConflictConfirmationOpen(false);
          store.loadLatest();
          setAssumptionsOpen(false);
        }}
        onOpenChange={setConflictConfirmationOpen}
        open={conflictConfirmationOpen}
        title="Încarci versiunea de pe disc?"
      />
    </div>
  );
}
