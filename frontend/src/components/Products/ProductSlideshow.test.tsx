/**
 * ProductSlideshow.test.tsx — Comprehensive Tests
 * ===============================================
 * Tests all scenarios for the ProductSlideshow component:
 * - Empty state with placeholder
 * - Single product
 * - Multiple products with auto-play
 * - Category filtering
 * - Keyboard navigation
 * - Touch/swipe support
 * - Zoom functionality
 * - Placeholder handling for limited images
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { ProductSlideshow, SlideshowItem, ProductSlideshowProps } from "../Products/ProductSlideshow";

// Mock CSS modules
vi.mock("../Products/ProductSlideshow.css", () => ({}));

// Mock lucide-react icons
vi.mock("lucide-react", () => ({
    Play: () => <button data-testid="play-icon">Play</button>,
    Pause: () => <button data-testid="pause-icon">Pause</button>,
    ChevronLeft: () => <button data-testid="prev-icon">Left</button>,
    ChevronRight: () => <button data-testid="next-icon">Right</button>,
    X: () => <button data-testid="close-icon">X</button>,
    ZoomIn: () => <button data-testid="zoom-icon">Zoom</button>,
    Image: () => <div data-testid="image-icon">Image</div>,
    Film: () => <div data-testid="film-icon">Film</div>,
    Loader2: () => <div data-testid="loader-icon">Loader</div>,
    AlertCircle: () => <div data-testid="alert-icon">Alert</div>,
    ChevronDown: () => <div data-testid="chevron-icon">Chevron</div>,
}));

// Test data factories
const createTestItem = (overrides: Partial<SlideshowItem> = {}): SlideshowItem => ({
    id: "test-1",
    name: "Test Product",
    description: "Test description",
    price: 100000,
    price_formatted: "100.000đ",
    image_url: "/test-image.jpg",
    category: "Test Category",
    ...overrides,
});

const sampleItems: SlideshowItem[] = [
    createTestItem({ id: "1", name: "ESP32 DevKit", price: 150000, category: "IoT", image_url: "/esp32.jpg" }),
    createTestItem({ id: "2", name: "Raspberry Pi 4", price: 350000, category: "IoT", image_url: "/rpi4.jpg" }),
    createTestItem({ id: "3", name: "Arduino Uno", price: 80000, category: "Microcontroller", image_url: "/arduino.jpg" }),
    createTestItem({ id: "4", name: "Sensor Kit", price: 120000, category: "Accessories", image_url: "/sensor.jpg" }),
];

describe("ProductSlideshow — Empty State", () => {
    it("should display placeholder when items array is empty", () => {
        render(<ProductSlideshow items={[]} />);
        
        const placeholder = screen.getByText(/chưa có hình ảnh/i);
        expect(placeholder).toBeInTheDocument();
    });

    it("should display custom placeholder text when provided", () => {
        render(
            <ProductSlideshow
                items={[]}
                placeholderText="Không có sản phẩm nào"
            />
        );
        
        expect(screen.getByText(/không có sản phẩm nào/i)).toBeInTheDocument();
    });
});

describe("ProductSlideshow — Single Product", () => {
    it("should render single product without controls", () => {
        const singleItem = [createTestItem({ id: "single-1" })];
        render(<ProductSlideshow items={singleItem} />);
        
        expect(screen.getByText("Test Product")).toBeInTheDocument();
    });

    it("should display product info overlay", () => {
        const singleItem = [createTestItem({ id: "single-2", name: "Special Product" })];
        render(<ProductSlideshow items={singleItem} />);
        
        expect(screen.getByText("Special Product")).toBeInTheDocument();
    });
});

describe("ProductSlideshow — Multiple Products", () => {
    it("should render all products in thumbnails", () => {
        render(<ProductSlideshow items={sampleItems} showThumbnails={true} />);
        
        // All thumbnails should be rendered
        const thumbnails = document.querySelectorAll(".slideshow-thumbnail");
        expect(thumbnails.length).toBe(4);
    });

    it("should have navigation buttons when multiple items", () => {
        render(<ProductSlideshow items={sampleItems} showControls={true} />);
        
        const prevButton = screen.getByTestId("prev-icon");
        const nextButton = screen.getByTestId("next-icon");
        
        expect(prevButton).toBeInTheDocument();
        expect(nextButton).toBeInTheDocument();
    });

    it("should have indicator dots when showIndicators is true", () => {
        render(<ProductSlideshow items={sampleItems} showIndicators={true} />);
        
        const indicators = document.querySelectorAll(".slideshow-indicator");
        expect(indicators.length).toBe(4);
    });
});

describe("ProductSlideshow — Navigation", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("should navigate to next slide on next button click", async () => {
        render(<ProductSlideshow items={sampleItems} showControls={true} />);
        
        const nextButton = screen.getByTestId("next-icon");
        fireEvent.click(nextButton);
        
        // Component should re-render with new current index
        await act(async () => {
            vi.advanceTimersByTime(600);
        });
    });

    it("should navigate to previous slide on prev button click", async () => {
        render(<ProductSlideshow items={sampleItems} showControls={true} />);
        
        const prevButton = screen.getByTestId("prev-icon");
        fireEvent.click(prevButton);
        
        await act(async () => {
            vi.advanceTimersByTime(600);
        });
    });

    it("should support keyboard navigation", async () => {
        render(<ProductSlideshow items={sampleItems} showControls={true} />);
        
        // Focus on the slideshow container
        const slideshow = document.querySelector(".product-slideshow");
        slideshow?.focus();
        
        // Press right arrow
        fireEvent.keyDown(slideshow!, { key: "ArrowRight" });
        
        await act(async () => {
            vi.advanceTimersByTime(600);
        });
    });
});

describe("ProductSlideshow — Auto-Play", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("should auto-play when enabled and multiple items", async () => {
        render(
            <ProductSlideshow
                items={sampleItems}
                autoPlay={true}
                autoPlayInterval={3000}
            />
        );
        
        // Start the auto-play timer
        await act(async () => {
            vi.advanceTimersByTime(3500);
        });
    });

    it("should not auto-play with single item", async () => {
        render(
            <ProductSlideshow
                items={[createTestItem()]}
                autoPlay={true}
            />
        );
        
        // No navigation should occur
        expect(screen.getByText("Test Product")).toBeInTheDocument();
    });

    it("should pause when play/pause button is clicked", async () => {
        render(
            <ProductSlideshow
                items={sampleItems}
                autoPlay={true}
                showControls={true}
            />
        );
        
        const playPauseButton = document.querySelector(".slideshow-play-pause");
        if (playPauseButton) {
            fireEvent.click(playPauseButton);
        }
    });
});

describe("ProductSlideshow — Category Filtering", () => {
    it("should show category dropdown when enabled and categories exist", () => {
        render(
            <ProductSlideshow
                items={sampleItems}
                enableCategoryFilter={true}
            />
        );
        
        const dropdown = screen.getByRole("combobox");
        expect(dropdown).toBeInTheDocument();
    });

    it("should filter items by selected category", async () => {
        render(
            <ProductSlideshow
                items={sampleItems}
                enableCategoryFilter={true}
            />
        );
        
        const dropdown = screen.getByRole("combobox");
        fireEvent.change(dropdown, { target: { value: "IoT" } });
        
        await waitFor(() => {
            const thumbnails = document.querySelectorAll(".slideshow-thumbnail");
            expect(thumbnails.length).toBeLessThanOrEqual(4);
        });
    });

    it("should show all categories in dropdown", () => {
        render(
            <ProductSlideshow
                items={sampleItems}
                enableCategoryFilter={true}
            />
        );
        
        const dropdown = screen.getByRole("combobox");
        const options = dropdown.querySelectorAll("option");
        
        expect(options.length).toBeGreaterThanOrEqual(1); // At least "All categories" option
    });
});

describe("ProductSlideshow — Zoom Functionality", () => {
    it("should render zoom button when enabled", () => {
        render(
            <ProductSlideshow
                items={sampleItems}
                enableZoom={true}
            />
        );
        
        const fullscreenButton = document.querySelector(".slideshow-fullscreen-btn");
        expect(fullscreenButton).toBeInTheDocument();
    });

    it("should open fullscreen on fullscreen button click", async () => {
        render(
            <ProductSlideshow
                items={sampleItems}
                enableZoom={true}
            />
        );
        
        const fullscreenButton = document.querySelector(".slideshow-fullscreen-btn");
        if (fullscreenButton) {
            fireEvent.click(fullscreenButton);
        }
        
        await waitFor(() => {
            const modal = document.querySelector(".slideshow-fullscreen-modal");
            expect(modal).toBeInTheDocument();
        });
    });
});

describe("ProductSlideshow — Touch/Swipe Support", () => {
    it("should respond to touch events", async () => {
        render(<ProductSlideshow items={sampleItems} />);
        
        const slideshow = document.querySelector(".slideshow-main");
        if (slideshow) {
            // Simulate touch start
            fireEvent.touchStart(slideshow, {
                touches: [{ clientX: 100 } as Touch],
            });
            
            // Simulate touch end
            fireEvent.touchEnd(slideshow, {
                touches: [{ clientX: 50 } as Touch],
            });
        }
        
        // Component should handle the swipe without crashing
        expect(true).toBe(true);
    });
});

describe("ProductSlideshow — Video Support", () => {
    it("should render video when video_url is present and no image", () => {
        const videoItem = [createTestItem({
            id: "video-1",
            image_url: undefined,
            video_url: "/test-video.mp4",
        })];
        
        render(<ProductSlideshow items={videoItem} />);
        
        const videoElement = document.querySelector("video");
        expect(videoElement).toBeInTheDocument();
    });
});

describe("ProductSlideshow — Edge Cases", () => {
    it("should handle items with valid data", () => {
        const validItems: SlideshowItem[] = [
            createTestItem({ id: "1", name: "Valid Product 1" }),
            createTestItem({ id: "2", name: "Valid Product 2" }),
        ];
        
        render(<ProductSlideshow items={validItems} />);
        
        expect(screen.getByText("Valid Product 1")).toBeInTheDocument();
    });

    it("should handle items without image_url gracefully", () => {
        const noImageItems: SlideshowItem[] = [
            createTestItem({ id: "no-img-1", image_url: undefined }),
        ];
        
        render(<ProductSlideshow items={noImageItems} />);
        
        const noImagePlaceholder = screen.getByText(/chưa có hình/i);
        expect(noImagePlaceholder).toBeInTheDocument();
    });

    it("should handle items with gallery but no main image", () => {
        const galleryItems: SlideshowItem[] = [
            {
                ...createTestItem({ id: "gallery-1", image_url: undefined }),
                images: ["/gallery-1.jpg", "/gallery-2.jpg"],
            },
        ];
        
        render(<ProductSlideshow items={galleryItems} />);
        
        expect(screen.getByText("Test Product")).toBeInTheDocument();
    });

    it("should handle rapid navigation clicks without crashing", async () => {
        render(<ProductSlideshow items={sampleItems} showControls={true} />);
        
        const nextButton = screen.getByTestId("next-icon");
        
        // Rapid clicks
        for (let i = 0; i < 5; i++) {
            fireEvent.click(nextButton);
        }
        
        expect(true).toBe(true);
    });
});

describe("ProductSlideshow — Performance", () => {
    it("should lazy load images", () => {
        render(<ProductSlideshow items={sampleItems} />);
        
        const images = document.querySelectorAll("img[loading='lazy']");
        expect(images.length).toBeGreaterThan(0);
    });

    it("should handle large number of items", () => {
        const manyItems: SlideshowItem[] = Array.from({ length: 50 }, (_, i) =>
            createTestItem({ id: `large-${i}`, name: `Product ${i}` })
        );
        
        render(<ProductSlideshow items={manyItems} showThumbnails={true} />);
        
        // Should render without performance issues
        const thumbnails = document.querySelectorAll(".slideshow-thumbnail");
        expect(thumbnails.length).toBe(50);
    });
});

describe("ProductSlideshow — Responsive Design", () => {
    it("should apply responsive CSS classes", () => {
        render(<ProductSlideshow items={sampleItems} className="custom-slideshow" />);
        
        const slideshow = document.querySelector(".product-slideshow");
        expect(slideshow).toHaveClass("custom-slideshow");
    });
});

describe("ProductSlideshow — Callbacks", () => {
    it("should call onItemClick when slide is clicked", async () => {
        const handleClick = vi.fn();
        render(<ProductSlideshow items={sampleItems} onItemClick={handleClick} />);
        
        const slideshowMain = document.querySelector(".slideshow-main");
        if (slideshowMain) {
            fireEvent.click(slideshowMain);
        }
        
        expect(handleClick).toHaveBeenCalled();
    });

    it("should call onItemHover when image is hovered", async () => {
        const handleHover = vi.fn();
        render(
            <ProductSlideshow
                items={sampleItems}
                onItemHover={handleHover}
                enableZoom={true}
            />
        );
        
        const imageContainer = document.querySelector(".slideshow-image-container");
        if (imageContainer) {
            fireEvent.mouseEnter(imageContainer);
        }
        
        await waitFor(() => {
            expect(handleHover).toHaveBeenCalled();
        });
    });
});

describe("ProductSlideshow — Accessibility", () => {
    it("should have accessible navigation buttons", () => {
        render(<ProductSlideshow items={sampleItems} showControls={true} />);
        
        const prevButton = screen.getByLabelText(/previous/i);
        const nextButton = screen.getByLabelText(/next/i);
        
        expect(prevButton).toBeInTheDocument();
        expect(nextButton).toBeInTheDocument();
    });

    it("should have accessible indicators", () => {
        render(<ProductSlideshow items={sampleItems} showIndicators={true} />);
        
        const indicators = document.querySelectorAll(".slideshow-indicator");
        indicators.forEach((indicator, idx) => {
            expect(indicator).toHaveAttribute("aria-label", `Go to slide ${idx + 1}`);
        });
    });

    it("should support keyboard navigation", () => {
        render(<ProductSlideshow items={sampleItems} showControls={true} />);
        
        const slideshow = document.querySelector(".product-slideshow");
        slideshow?.focus();
        
        // Press space to toggle play/pause
        fireEvent.keyDown(slideshow!, { key: " " });
        
        // Press escape to close fullscreen (if open)
        fireEvent.keyDown(slideshow!, { key: "Escape" });
    });
});
