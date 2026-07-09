import React from "react";
import { cn } from "@/lib/utils";

type PageContainerProps = React.HTMLAttributes<HTMLDivElement>;

export const PageContainer: React.FC<PageContainerProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <div className={cn("mx-auto flex w-full max-w-7xl flex-col gap-6", className)} {...props}>
      {children}
    </div>
  );
};
