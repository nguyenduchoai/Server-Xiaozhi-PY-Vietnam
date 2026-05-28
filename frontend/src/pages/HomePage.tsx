import { useEffect, useState } from "react";
import { useBrand } from "@/hooks/useBrand";
import { ModernLandingPage } from "./brands/XiaozhiLandingPage";

export function HomePage() {
  const brand = useBrand();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Small delay to ensure brand is loaded
    const timer = setTimeout(() => setLoading(false), 100);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-teal-400 border-r-transparent"></div>
          <p className="text-gray-400">Đang tải...</p>
        </div>
      </div>
    );
  }

  return <ModernLandingPage brand={brand} />;
}

export default HomePage;
