import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AgentBannerPanel } from "./AgentBannerPanel";
import { agentsApi } from "@/services/api";

vi.mock("@/services/api", () => ({
    agentsApi: {
        updateAgent: vi.fn().mockResolvedValue({ success: true }),
        getAgent: vi.fn().mockResolvedValue({}),
        deleteAgent: vi.fn().mockResolvedValue({}),
        listAgents: vi.fn().mockResolvedValue([]),
    }
}));

describe("AgentBannerPanel Component", () => {
    const mockRefresh = vi.fn();
    const mockAgent = {
        banner_images: [
            {
                url: "http://example.com/banner1.jpg",
                duration: 5,
                transition: "fade",
                scale_mode: "cover"
            }
        ]
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders the Banner panel correctly", () => {
        render(<AgentBannerPanel agentId="123" agent={mockAgent} onRefresh={mockRefresh} />);
        
        expect(screen.getByText(/Cấu hình Kiosk Banner/i)).toBeInTheDocument();
    });

    it("shows Live Preview button when banners exist", () => {
        render(<AgentBannerPanel agentId="123" agent={mockAgent} onRefresh={mockRefresh} />);
        
        const previewBtn = screen.getByRole("button", { name: /Live Preview/i });
        expect(previewBtn).toBeInTheDocument();
    });

    it("opens the live preview modal on click", async () => {
        render(<AgentBannerPanel agentId="123" agent={mockAgent} onRefresh={mockRefresh} />);
        
        const previewBtn = screen.getByRole("button", { name: /Live Preview/i });
        fireEvent.click(previewBtn);
        
        await waitFor(() => {
            expect(screen.getAllByText(/Full HD/i).length).toBeGreaterThanOrEqual(1);
        });
    });
});
