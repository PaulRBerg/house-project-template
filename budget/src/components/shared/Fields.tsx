import { useEffect, useId, useRef, useState } from "react";

import { formatDate, formatMoneyInput, parseDateInput, parseEuroToCents } from "../../ui/format.js";
import { fieldStyles, moneyInputStyles } from "./styles.js";

interface MoneyInputProps {
  label: string;
  cents: number;
  onChange: (cents: number) => void;
  disabled?: boolean;
  minCents?: number;
  hint?: string;
}

export function MoneyInput({
  label,
  cents,
  onChange,
  disabled = false,
  minCents = 0,
  hint,
}: MoneyInputProps) {
  const [value, setValue] = useState(() => formatMoneyInput(cents));
  const [invalid, setInvalid] = useState(false);
  const focused = useRef(false);
  const input = useRef<HTMLInputElement>(null);
  const id = useId();

  useEffect(() => {
    if (focused.current) return;
    const timer = window.setTimeout(() => {
      setValue(formatMoneyInput(cents));
      setInvalid(false);
      input.current?.setCustomValidity("");
    }, 0);
    return () => window.clearTimeout(timer);
  }, [cents]);

  return (
    <label data-field className={fieldStyles} htmlFor={id}>
      <span>{label}</span>
      <span className={moneyInputStyles}>
        <input
          aria-invalid={invalid}
          disabled={disabled}
          id={id}
          inputMode="decimal"
          onChange={(event) => {
            const next = event.target.value;
            setValue(next);
            const parsed = parseEuroToCents(next);
            const isInvalid = parsed === null || parsed < minCents;
            event.currentTarget.setCustomValidity(isInvalid ? "Introdu o sumă EUR validă." : "");
            setInvalid(isInvalid);
            if (!isInvalid && parsed !== null) onChange(parsed);
          }}
          onBlur={(event) => {
            focused.current = false;
            const parsed = parseEuroToCents(event.currentTarget.value);
            if (parsed !== null && parsed >= minCents) {
              setValue(formatMoneyInput(parsed));
            }
          }}
          onFocus={() => {
            focused.current = true;
          }}
          ref={input}
          required
          value={value}
        />
        <b>EUR</b>
      </span>
      {hint && <small>{hint}</small>}
      {invalid && <small className="text-danger!">Introdu o sumă EUR validă.</small>}
    </label>
  );
}

interface DateInputProps {
  name: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  readOnly?: boolean;
  required?: boolean;
}

export function DateInput({
  name,
  value,
  onChange,
  disabled = false,
  readOnly = false,
  required = false,
}: DateInputProps) {
  const [displayValue, setDisplayValue] = useState(() => (value ? formatDate(value) : ""));
  const focused = useRef(false);
  const input = useRef<HTMLInputElement>(null);
  const dateInvalid = required
    ? parseDateInput(displayValue) === null
    : !!displayValue && !parseDateInput(displayValue);

  useEffect(() => {
    if (focused.current) return;
    setDisplayValue(value ? formatDate(value) : "");
    input.current?.setCustomValidity("");
  }, [value]);

  return (
    <input
      aria-invalid={dateInvalid}
      disabled={disabled}
      name={name}
      onBlur={(event) => {
        focused.current = false;
        const parsed = parseDateInput(event.currentTarget.value);
        if (parsed) setDisplayValue(formatDate(parsed));
      }}
      onChange={(event) => {
        const next = event.target.value;
        setDisplayValue(next);
        if (!next && !required) {
          event.currentTarget.setCustomValidity("");
          onChange("");
          return;
        }
        const parsed = parseDateInput(next);
        const invalid = parsed === null;
        event.currentTarget.setCustomValidity(invalid ? "Introdu data ca 7 Sep 2027." : "");
        if (parsed) onChange(parsed);
      }}
      onFocus={() => {
        focused.current = true;
      }}
      placeholder="7 Sep 2027"
      readOnly={readOnly}
      ref={input}
      required={required}
      value={displayValue}
    />
  );
}
