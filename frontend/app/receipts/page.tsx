"use client";

import { useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import { LoadingState } from "@/components/ui/states";

function ReceiptsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/more?tab=activity");
  }, [router]);

  return <LoadingState message="Opening Activity & Receipts…" />;
}

export default function ReceiptsPage() {
  return (
    <Suspense fallback={<LoadingState message="Opening Activity & Receipts…" />}>
      <ReceiptsRedirect />
    </Suspense>
  );
}
