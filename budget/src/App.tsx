import { Tabs } from "@base-ui/react/tabs";
import { CircleAlert, House, Landmark, RotateCcw, Users, WalletCards } from "lucide-react";
import { parseAsString, parseAsStringLiteral, useQueryState } from "nuqs";
import { useEffect, useMemo, useState } from "react";

import { BNR_EXCHANGE_RATE_PAGE_URL } from "./api/contracts.js";
import { BeneficiariesView } from "./components/beneficiaries/BeneficiariesView.js";
import { AssumptionsDialog } from "./components/budget/AssumptionsDialog.js";
import { BudgetTable } from "./components/budget/BudgetTable.js";
import {
  BudgetToolbar,
  type CostScopeFilter,
  type StatusFilter,
} from "./components/budget/BudgetToolbar.js";
import {
  BUDGET_GROUPINGS,
  DEFAULT_CATEGORY_ID,
  EXTRAS_CATEGORY_ID,
  supportsRoomGrouping,
} from "./components/budget/categories.js";
import { ItemDetails } from "./components/budget/ItemDetails.js";
import { ProjectOverview } from "./components/budget/ProjectOverview.js";
import { StageStrip } from "./components/budget/StageStrip.js";
import { CashFlowView } from "./components/cash-flow/CashFlowView.js";
import { AnimatedView } from "./components/shared/AnimatedView.js";
import { AppButton } from "./components/shared/AppButton.js";
import { AppSelect } from "./components/shared/AppSelect.js";
import { cn, emptyStatePanelStyles } from "./components/shared/styles.js";
import {
  EXTRA_MILESTONE_ID,
  getBeneficiaryBundles,
  selectBudgetView,
  type Milestone,
} from "./domain/index.js";
import { useBudgetSnapshot } from "./hooks/useBudgetSnapshot.js";
import { useExchangeRate, type UseExchangeRateResult } from "./hooks/useExchangeRate.js";
import { localCalendarDate } from "./ui/format.js";

const NAVIGATION = [
  { id: "budget", label: "Buget", icon: Landmark },
  { id: "flux", label: "Flux", icon: WalletCards },
  { id: "beneficiari", label: "Beneficiari", icon: Users },
] as const;

const APP_PAGES = NAVIGATION.map(({ id }) => id);

const statusPageStyles =
  "flex min-h-screen flex-col items-center justify-center p-7.5 text-center [&_h1]:mt-3 [&_h1]:text-[2rem] [&_h1]:tracking-[-0.04em]";

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
  const budget = useBudgetSnapshot();
  const exchangeRate = useExchangeRate();
  const exchangeRateHeader = formatExchangeRateHeader(exchangeRate);
  const [activePage, setActivePage] = useQueryState(
    "page",
    parseAsStringLiteral(APP_PAGES).withDefault("budget").withOptions({ history: "push" }),
  );
  const [category, setCategory] = useQueryState(
    "category",
    parseAsString.withDefault(DEFAULT_CATEGORY_ID).withOptions({ history: "push" }),
  );
  const [grouping, setGrouping] = useQueryState(
    "grouping",
    parseAsStringLiteral(BUDGET_GROUPINGS).withDefault("rooms").withOptions({ history: "push" }),
  );
  const [beneficiaryId, setBeneficiaryId] = useQueryState(
    "beneficiar",
    parseAsString.withOptions({ history: "push" }),
  );
  const [cashFlowMilestone, setCashFlowMilestone] = useState<Milestone["id"] | "all">("all");
  const [search, setSearch] = useState("");
  const [costScope, setCostScope] = useState<CostScopeFilter>("all");
  const [status, setStatus] = useState<StatusFilter>("active");
  const filters = useMemo(() => ({ search, costScope, status }), [search, costScope, status]);
  const [assumptionsMounted, setAssumptionsMounted] = useState(false);
  const [assumptionsOpen, setAssumptionsOpen] = useState(false);
  const [itemDetailsId, setItemDetailsId] = useState<string | null>(null);
  const [itemDetailsOpen, setItemDetailsOpen] = useState(false);
  // Overdue and upcoming state follows the calendar day, refreshed when the tab regains focus.
  const [asOf, setAsOf] = useState(localCalendarDate);
  useEffect(() => {
    const refresh = (): void => setAsOf(localCalendarDate());
    window.addEventListener("focus", refresh);
    window.document.addEventListener("visibilitychange", refresh);
    return () => {
      window.removeEventListener("focus", refresh);
      window.document.removeEventListener("visibilitychange", refresh);
    };
  }, []);
  const document = budget.document;
  const view = useMemo(
    () => (document ? selectBudgetView(document, { asOf, scope: "all" }) : undefined),
    [asOf, document],
  );
  const initialView = useMemo(
    () => (document ? selectBudgetView(document, { asOf }) : undefined),
    [asOf, document],
  );
  const bundles = useMemo(
    () => (document && view ? getBeneficiaryBundles(document, view) : []),
    [document, view],
  );
  if (budget.loadState === "loading") {
    return (
      <main className={statusPageStyles} aria-busy="true">
        <House className="text-accent" aria-hidden="true" size={28} />
        <h1>Casa noastră</h1>
        <p className="mt-1.5 mb-4.5 max-w-150 text-muted">Se încarcă bugetul local…</p>
      </main>
    );
  }

  if (budget.loadState === "error" || !document || !view || !initialView) {
    return (
      <main className={statusPageStyles}>
        <CircleAlert className="text-accent" aria-hidden="true" size={28} />
        <h1>Bugetul local nu poate fi deschis</h1>
        <p className="mt-1.5 mb-4.5 max-w-150 text-muted" role="alert">
          {budget.loadError ?? "Serverul nu a returnat un document valid."}
        </p>
        <AppButton intent="primary" onClick={() => void budget.reload()} type="button">
          <RotateCcw className="text-accent" aria-hidden="true" size={16} /> Reîncearcă
        </AppButton>
      </main>
    );
  }

  const requestAssumptions = (): void => {
    setAssumptionsMounted(true);
    setAssumptionsOpen(true);
  };
  const requestItemDetails = (id: string): void => {
    setItemDetailsId(id);
    setItemDetailsOpen(true);
  };
  const requestBeneficiary = (id: string): void => {
    void setActivePage("beneficiari");
    void setBeneficiaryId(id);
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
          aria-label="Casa noastră, mergi la conținut"
        >
          <House className="text-accent" aria-hidden="true" size={19} />
          <span>Casa noastră</span>
        </a>
        <nav className="flex gap-1 self-stretch" aria-label="Secțiuni principale">
          {NAVIGATION.map(({ id, label, icon: Icon }) => (
            <button
              className="inline-flex items-center gap-1.75 border-0 border-b-2 border-transparent bg-transparent px-3.75 text-[0.79rem] font-bold text-muted hover:text-ink aria-[current=page]:border-accent aria-[current=page]:text-ink [&[aria-current=page]_svg]:text-accent"
              aria-current={activePage === id ? "page" : undefined}
              key={id}
              onClick={() => void setActivePage(id)}
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

      <main className="mx-auto max-w-385 px-gutter pt-8 pb-20" id="main-content">
        <AnimatedView value={activePage}>
          {(displayedPage) => (
            <>
              {displayedPage === "budget" && (
                <Tabs.Root
                  onValueChange={(id) => {
                    if (typeof id !== "string") return;
                    void setCategory(id);
                    if (!supportsRoomGrouping(id)) void setGrouping("rooms");
                  }}
                  value={selectedCategory}
                >
                  <h1 className="sr-only">Buget</h1>
                  <ProjectOverview view={initialView} project={document.project} />
                  <StageStrip view={view} />
                  <BudgetToolbar
                    costScope={costScope}
                    onCostScopeChange={setCostScope}
                    onOpenAssumptions={requestAssumptions}
                    onSearchChange={setSearch}
                    onStatusChange={setStatus}
                    search={search}
                    status={status}
                  />
                  {document.items.length === 0 ? (
                    <section className={cn(emptyStatePanelStyles, "mt-10 [&_h2]:text-ink")}>
                      <h2>Bugetul nu conține încă elemente</h2>
                      <p className="mx-auto mt-2 max-w-155">
                        Documentul local a fost încărcat corect. Nu există costuri sau plăți de
                        afișat.
                      </p>
                    </section>
                  ) : (
                    <Tabs.Panel keepMounted value={selectedCategory}>
                      {selectedCategory === EXTRAS_CATEGORY_ID && (
                        <p
                          className="my-4 border-l-3 border-stage pl-3 text-[0.82rem] text-muted"
                          data-stage={EXTRA_MILESTONE_ID}
                        >
                          Dotări după mutare · iunie 2029 – iunie 2031. Buget separat, exclus din
                          „Rămas de plată”. Dotările rămân în brief și în modelul casei.
                        </p>
                      )}
                      <BudgetTable
                        beneficiaries={document.beneficiaries}
                        filters={filters}
                        grouping={grouping}
                        hierarchy={view.hierarchy}
                        onGroupingChange={(nextGrouping) => void setGrouping(nextGrouping)}
                        onOpenBeneficiary={requestBeneficiary}
                        onOpenItem={requestItemDetails}
                        selectedCategory={selectedCategory}
                      />
                    </Tabs.Panel>
                  )}
                </Tabs.Root>
              )}
              {displayedPage === "flux" && (
                <>
                  <section
                    className="flex items-center justify-end gap-2.5"
                    aria-label="Controale planificare"
                  >
                    <div className="flex min-w-0 items-center gap-1.5 text-[0.72rem] font-[680]">
                      <span>Etapă</span>
                      <AppSelect
                        className="min-w-52 flex-1 text-[0.82rem] font-medium"
                        label="Etapă"
                        name="cash-flow-milestone"
                        onValueChange={setCashFlowMilestone}
                        options={[
                          { value: "all", label: "Până la mutare" },
                          ...document.milestones.map((entry) => ({
                            value: entry.id,
                            label: entry.label,
                          })),
                        ]}
                        value={cashFlowMilestone}
                      />
                    </div>
                    <AppButton intent="secondary" onClick={requestAssumptions} type="button">
                      Ipoteze
                    </AppButton>
                  </section>
                  <div className="mt-7">
                    <CashFlowView
                      milestoneId={cashFlowMilestone}
                      onOpenItem={requestItemDetails}
                      view={cashFlowMilestone === EXTRA_MILESTONE_ID ? view : initialView}
                    />
                  </div>
                </>
              )}
              {displayedPage === "beneficiari" && (
                <>
                  <p className="mb-4 text-[0.78rem] text-muted">
                    Toate costurile pe beneficiari, inclusiv etapa Extra.
                  </p>
                  <BeneficiariesView
                    bundles={bundles}
                    document={document}
                    onOpenItem={requestItemDetails}
                    onSelect={(id) => void setBeneficiaryId(id)}
                    selectedId={beneficiaryId}
                  />
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

      {assumptionsMounted && (
        <AssumptionsDialog
          onClose={() => {
            setAssumptionsOpen(false);
          }}
          onExited={() => {
            setAssumptionsMounted(false);
          }}
          open={assumptionsOpen}
        />
      )}
    </div>
  );
}
