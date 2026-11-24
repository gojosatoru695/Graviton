"use client";

import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { UploadModal } from "@/components/upload/upload-modal";
import { AskJarvisDrawer } from "@/components/chat/ask-jarvis-drawer";

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-[#080B14] text-[#F4F6FF] font-sans antialiased selection:bg-[#8065FF]/30 selection:text-[#F4F6FF]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 pb-16 lg:pb-0 overflow-x-hidden">{children}</main>
      </div>
      <UploadModal />
      <AskJarvisDrawer />
    </div>
  );
}
