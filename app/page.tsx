"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to pixel-office
    router.push("/pixel-office");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-[var(--text-muted)]">正在跳转到像素办公室...</div>
    </div>
  );
}
