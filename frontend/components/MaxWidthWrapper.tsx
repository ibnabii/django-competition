import React, { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface MaxWidthWrapperProps extends HTMLAttributes<HTMLDivElement> {
  className?: string;
}

const MaxWidthWrapper = ({
  className,
  children,
  ...props
}: MaxWidthWrapperProps) => {
  return (
    <div
      className={cn("m-auto w-full max-w-screen-xl px-2 md:px-20", className)}
      {...props}
    >
      {children}
    </div>
  );
};

export default MaxWidthWrapper;
