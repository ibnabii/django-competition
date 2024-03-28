import React from "react";

import MaxWidthWrapper from "@/components/MaxWidthWrapper";

interface CompetitionPageProps {
  params: {
    id: string;
  };
}

const CompetitionPage = ({ params: { id } }: CompetitionPageProps) => {
  return (
    <MaxWidthWrapper className="py-10">
      <h1 className="text-center text-3xl">{id}</h1>
      <ul>
        <li>competition description</li>
        <li>functionalities</li>
      </ul>
    </MaxWidthWrapper>
  );
};

export default CompetitionPage;
