import { loadExchangeRate } from "../api/client.js";
import type { ExchangeRate } from "../api/contracts.js";
import { useAsyncResource, type LoadStatus } from "./useAsyncResource.js";

export interface UseExchangeRateResult {
  status: LoadStatus;
  rate?: ExchangeRate | undefined;
}

export function useExchangeRate(): UseExchangeRateResult {
  const { status, value } = useAsyncResource(loadExchangeRate);
  return { status, rate: value };
}
