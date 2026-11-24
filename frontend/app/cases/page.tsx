"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LoadingState } from "@/components/ui/states";

function CasesRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const params = searchParams.toString();
    router.replace(`/tasks${params ? `?${params}` : ""}`);
  }, [router, searchParams]);

  return <LoadingState message="Opening Tasks & Issues…" />;
}

export default function CasesPage() {
  return (
    <Suspense fallback={<LoadingState message="Opening Tasks & Issues…" />}>
      <CasesRedirect />
    </Suspense>
  );
}
