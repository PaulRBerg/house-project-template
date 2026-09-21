import { useEffect, useState } from "react";

import { loadExchangeRate } from "../api/client.js";
import type { ExchangeRate } from "../api/contracts.js";

export type ExchangeRateStatus = "loading" | "ready" | "error";

export interface UseExchangeRateResult {
  status: ExchangeRateStatus;
  rate?: ExchangeRate | undefined;
}

export function useExchangeRate(): UseExchangeRateResult {
  const [status, setStatus] = useState<ExchangeRateStatus>("loading");
  const [rate, setRate] = useState<ExchangeRate>();

  useEffect(() => {
    let active = true;
    void loadExchangeRate().then(
      (next) => {
        if (!active) return;
        setRate(next);
        setStatus("ready");
      },
      () => {
        if (!active) return;
        setStatus("error");
      },
    );
    return () => {
      active = false;
    };
  }, []);

  return { status, rate };
}
