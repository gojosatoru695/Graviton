// ─── API layer with TanStack Query hooks ───

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  MOCK_DASHBOARD,
  MOCK_CASES,
  MOCK_CASE_DETAILS,
  MOCK_CASE_DETAIL,
  MOCK_MONEY_RECONCILIATION,
  MOCK_SETTLEMENTS,
  MOCK_PROMISES,
  MOCK_RECEIPTS,
} from "./mock-data";
import type {
  DashboardSummary,
  UrgentCase,
  CaseListItem,
  CaseDetail,
  MoneyReconciliation,
  SettlementData,
  Promise as PromiseType,
  ReceiptItem,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

// Simulate network delay for realistic loading states
function delay(ms = 400): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

// ─── Fetch helpers ───
async function fetchJson<T>(path: string, fallback: T): Promise<T> {
  if (USE_MOCK) {
    await delay();
    return fallback;
  }
  try {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    if (!res.ok) {
      console.warn(`API ${path} returned ${res.status}, falling back to fixtures.`);
      return fallback;
    }
    return await res.json();
  } catch (err) {
    console.warn(`Network error reaching API ${path}, falling back to fixtures:`, err);
    return fallback;
  }
}

// ─── Dashboard ───
export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => fetchJson<{ metrics: DashboardSummary; urgent_cases: UrgentCase[] }>("/dashboard/summary", MOCK_DASHBOARD),
    staleTime: 30_000,
  });
}

// ─── Cases ───
export function useCases() {
  return useQuery({
    queryKey: ["cases"],
    queryFn: () => fetchJson<CaseListItem[]>("/cases", MOCK_CASES),
    staleTime: 15_000,
  });
}

export function useCaseDetail(caseId: string | null) {
  return useQuery({
    queryKey: ["case-detail", caseId],
    queryFn: async (): Promise<CaseDetail | null> => {
      if (!caseId) return null;
      if (USE_MOCK) {
        await delay(300);
        return MOCK_CASE_DETAILS[caseId] || {
          ...MOCK_CASE_DETAIL,
          id: caseId,
          title: `Case ${caseId}`,
        };
      }
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}`, { cache: "no-store" });
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn(`Failed to load case detail from ${API_BASE}/cases/${caseId}:`, err);
      }
      return MOCK_CASE_DETAILS[caseId] || {
        ...MOCK_CASE_DETAIL,
        id: caseId,
        title: `Case ${caseId}`,
      };
    },
    enabled: !!caseId,
    staleTime: 10_000,
  });
}

// ─── Money ───
export function useMoneyReconciliation() {
  return useQuery({
    queryKey: ["money-reconciliation"],
    queryFn: () => fetchJson<MoneyReconciliation>("/money/reconciliation", MOCK_MONEY_RECONCILIATION),
    staleTime: 30_000,
  });
}

export function useSettlements() {
  return useQuery({
    queryKey: ["settlements"],
    queryFn: () => fetchJson<SettlementData[]>("/money/settlements", MOCK_SETTLEMENTS),
    staleTime: 30_000,
  });
}

// ─── Promises ───
export function usePromises() {
  return useQuery({
    queryKey: ["promises"],
    queryFn: () => fetchJson<PromiseType[]>("/promises", MOCK_PROMISES),
    staleTime: 30_000,
  });
}

// ─── Receipts ───
export function useReceipts() {
  return useQuery({
    queryKey: ["receipts"],
    queryFn: () => fetchJson<ReceiptItem[]>("/receipts", MOCK_RECEIPTS),
    staleTime: 30_000,
  });
}

// ─── Action Decision Mutation ───
export function useActionDecision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      actionId,
      decision,
      rejectionReason,
    }: {
      actionId: string;
      decision: "APPROVED" | "REJECTED" | "DRAFT";
      rejectionReason?: string;
    }) => {
      if (USE_MOCK) {
        await delay(600);
        return { status: "success", decision, actionId, rejectionReason };
      }
      const res = await fetch(`${API_BASE}/actions/${actionId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, rejection_reason: rejectionReason }),
      });
      if (!res.ok) throw new Error("Action decision failed");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      queryClient.invalidateQueries({ queryKey: ["case-detail"] });
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

// ─── Run Investigation Mutation ───
export function useRunInvestigation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await delay(1200);
      return {
        status: "complete",
        scannedRecords: {
          orders: 60,
          bankCredits: 47,
          whatsappMessages: 184,
          marketplaceSettlements: 1,
        },
        findingsCount: 5,
        newAnomalies: 1,
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      queryClient.invalidateQueries({ queryKey: ["money-reconciliation"] });
      queryClient.invalidateQueries({ queryKey: ["promises"] });
    },
  });
}
