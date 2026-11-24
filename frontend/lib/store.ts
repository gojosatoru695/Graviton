import { create } from "zustand";

// ─── UI Store ───
interface UIState {
  sidebarCollapsed: boolean;
  mobileNavOpen: boolean;
  uploadModalOpen: boolean;
  askJarvisOpen: boolean;
  searchQuery: string;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setMobileNavOpen: (open: boolean) => void;
  setUploadModalOpen: (open: boolean) => void;
  setAskJarvisOpen: (open: boolean) => void;
  setSearchQuery: (q: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  mobileNavOpen: false,
  uploadModalOpen: false,
  askJarvisOpen: false,
  searchQuery: "",
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setMobileNavOpen: (open) => set({ mobileNavOpen: open }),
  setUploadModalOpen: (open) => set({ uploadModalOpen: open }),
  setAskJarvisOpen: (open) => set({ askJarvisOpen: open }),
  setSearchQuery: (q) => set({ searchQuery: q }),
}));

// ─── Cases Store ───
export type GraphViewMode = "graph" | "timeline" | "evidence";

interface CasesState {
  selectedCaseId: string | null;
  selectedNodeId: string | null;
  filterType: string;
  filterStatus: string;
  viewMode: GraphViewMode;
  setSelectedCaseId: (id: string | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  setFilterType: (type: string) => void;
  setFilterStatus: (status: string) => void;
  setViewMode: (mode: GraphViewMode) => void;
}

export const useCasesStore = create<CasesState>((set) => ({
  selectedCaseId: "case_001",
  selectedNodeId: null,
  filterType: "ALL",
  filterStatus: "ALL",
  viewMode: "graph",
  setSelectedCaseId: (id) => set({ selectedCaseId: id, selectedNodeId: null }),
  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),
  setFilterType: (type) => set({ filterType: type }),
  setFilterStatus: (status) => set({ filterStatus: status }),
  setViewMode: (mode) => set({ viewMode: mode }),
}));

// ─── Money Store ───
interface MoneyState {
  activeTab: "settlements" | "reconciliation";
  selectedTxnId: string | null;
  setActiveTab: (tab: "settlements" | "reconciliation") => void;
  setSelectedTxnId: (id: string | null) => void;
}

export const useMoneyStore = create<MoneyState>((set) => ({
  activeTab: "settlements",
  selectedTxnId: null,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedTxnId: (id) => set({ selectedTxnId: id }),
}));

// ─── Promises Store ───
interface PromisesState {
  selectedPromiseId: string | null;
  filterStatus: string;
  setSelectedPromiseId: (id: string | null) => void;
  setFilterStatus: (status: string) => void;
}

export const usePromisesStore = create<PromisesState>((set) => ({
  selectedPromiseId: null,
  filterStatus: "ALL",
  setSelectedPromiseId: (id) => set({ selectedPromiseId: id }),
  setFilterStatus: (status) => set({ filterStatus: status }),
}));

// ─── Receipts Store ───
interface ReceiptsState {
  selectedReceiptId: string | null;
  setSelectedReceiptId: (id: string | null) => void;
}

export const useReceiptsStore = create<ReceiptsState>((set) => ({
  selectedReceiptId: null,
  setSelectedReceiptId: (id) => set({ selectedReceiptId: id }),
}));
