import React from "react";

import MaxWidthWrapper from "@/components/MaxWidthWrapper";
import Link from "next/link";

const Navbar = () => {
  return (
    <div className="sticky left-0 top-0 w-full py-4">
      <MaxWidthWrapper>
        <div className="flex justify-between">
          <Link href="/">LOGO</Link>
          <div className="space-x-4">
            <Link href="/">Competitions</Link>
            <Link href="/sign-up">Sign up</Link>
            <Link href="/sign-in">Sign in</Link>
          </div>
        </div>
      </MaxWidthWrapper>
    </div>
  );
};

export default Navbar;
