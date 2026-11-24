"use client";

import { useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import { LoadingState } from "@/components/ui/states";

function PromisesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/tasks?filter=BROKEN_PROMISE");
  }, [router]);

  return <LoadingState message="Opening Promises in Tasks…" />;
}

export default function PromisesPage() {
  return (
    <Suspense fallback={<LoadingState message="Opening Promises in Tasks…" />}>
      <PromisesRedirect />
    </Suspense>
  );
}
