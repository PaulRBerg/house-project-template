import { useCallback, useEffect, useRef, useState } from "react";

import { BudgetApiError, BudgetConflictError, loadBudget, saveBudget } from "../api/client.js";
import type { BudgetSnapshot } from "../api/contracts.js";
import {
  budgetDocumentSchema,
  formatValidationIssues,
  type BudgetDocument,
} from "../domain/index.js";

export type LoadState = "loading" | "ready" | "error";
export type SaveState = "idle" | "saving" | "saved" | "error" | "conflict";

interface FailedSave {
  document: BudgetDocument;
  message: string;
}

function messageFrom(error: unknown): string {
  if (error instanceof BudgetApiError) {
    return [error.message, ...error.details].filter(Boolean).join(" ");
  }
  if (error instanceof TypeError) {
    return "Nu se poate contacta serverul local. Verifică dacă aplicația rulează și reîncearcă.";
  }
  return error instanceof Error ? error.message : "Bugetul nu a putut fi salvat.";
}

export function useBudgetStore() {
  const [snapshot, setSnapshot] = useState<BudgetSnapshot>();
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string>();
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [failedSave, setFailedSave] = useState<FailedSave>();
  const [conflict, setConflict] = useState<BudgetConflictError>();
  const saving = useRef(false);

  const reload = useCallback(async () => {
    setLoadState("loading");
    setLoadError(undefined);
    try {
      const next = await loadBudget();
      setSnapshot(next);
      setLoadState("ready");
      setSaveState("idle");
    } catch (error) {
      setLoadState("error");
      setLoadError(messageFrom(error));
    }
  }, []);

  useEffect(() => {
    let active = true;
    void loadBudget().then(
      (next) => {
        if (!active) return;
        setSnapshot(next);
        setLoadState("ready");
        setSaveState("idle");
      },
      (error: unknown) => {
        if (!active) return;
        setLoadState("error");
        setLoadError(messageFrom(error));
      },
    );
    return () => {
      active = false;
    };
  }, []);

  const persist = useCallback(
    async (document: BudgetDocument): Promise<boolean> => {
      if (!snapshot || saving.current) return false;
      const parsed = budgetDocumentSchema.safeParse(document);
      if (!parsed.success) {
        setFailedSave({
          document,
          message: formatValidationIssues(parsed.error).slice(0, 4).join(" "),
        });
        setSaveState("error");
        return false;
      }
      saving.current = true;
      setSaveState("saving");
      setFailedSave(undefined);
      setConflict(undefined);
      try {
        const next = await saveBudget(snapshot.revision, parsed.data);
        setSnapshot(next);
        setSaveState("saved");
        return true;
      } catch (error) {
        const failure = { document: parsed.data, message: messageFrom(error) };
        setFailedSave(failure);
        if (error instanceof BudgetConflictError) {
          setConflict(error);
          setSaveState("conflict");
        } else {
          setSaveState("error");
        }
        return false;
      } finally {
        saving.current = false;
      }
    },
    [snapshot],
  );

  const retry = useCallback(async () => {
    if (!failedSave) return false;
    return await persist(failedSave.document);
  }, [failedSave, persist]);

  const loadLatest = useCallback(() => {
    if (!conflict) return;
    setSnapshot(conflict.latest);
    setConflict(undefined);
    setFailedSave(undefined);
    setSaveState("idle");
  }, [conflict]);

  return {
    snapshot,
    document: snapshot?.document,
    loadState,
    loadError,
    saveState,
    saveError: failedSave?.message,
    unsavedDocument: failedSave?.document,
    conflict,
    busy: saveState === "saving",
    reload,
    persist,
    retry,
    loadLatest,
  };
}
