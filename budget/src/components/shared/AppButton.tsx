import { Button as BaseButton } from "@base-ui/react/button";
import type { ComponentProps } from "react";
import type { VariantProps } from "tailwind-variants";

import { buttonVariants } from "./styles.js";

type AppButtonProps = Omit<ComponentProps<typeof BaseButton>, "className"> &
  VariantProps<typeof buttonVariants> & {
    className?: string;
  };

export function AppButton({ className, intent, ...props }: AppButtonProps) {
  return <BaseButton className={buttonVariants({ class: className, intent })} {...props} />;
}
