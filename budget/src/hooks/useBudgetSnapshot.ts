import { BudgetApiError, loadBudget } from "../api/client.js";
import { useAsyncResource } from "./useAsyncResource.js";

function messageFrom(error: unknown): string {
  if (error instanceof BudgetApiError) {
    return [error.message, ...error.details].filter(Boolean).join(" ");
  }
  if (error instanceof TypeError) {
    return "Nu se poate contacta serverul local. Verifică dacă aplicația rulează și reîncearcă.";
  }
  return error instanceof Error ? error.message : "Bugetul nu a putut fi încărcat.";
}

export function useBudgetSnapshot() {
  const { status, value, error, reload } = useAsyncResource(loadBudget);
  return {
    document: value?.document,
    loadState: status,
    loadError: status === "error" ? messageFrom(error) : undefined,
    reload,
  };
}
