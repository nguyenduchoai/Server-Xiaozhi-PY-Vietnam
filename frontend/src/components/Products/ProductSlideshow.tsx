/**
 * ProductSlideshow - Professional Slideshow Component for Sales Module
 * 
 * Features:
 * - Responsive design with smooth transitions
 * - Auto-play, pause, and manual slide controls
 * - Image and video support
 * - Placeholder handling for limited images
 * - Category filtering
 * - Zoom effect on hover
 * - Lazy loading for performance
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { clsx } from 'clsx';
import {
    Play, Pause, ChevronLeft, ChevronRight, X, ZoomIn,
    Image as ImageIcon, Film, Loader2, AlertCircle, ChevronDown
} from 'lucide-react';
import './ProductSlideshow.css';

export interface SlideshowItem {
    id: string;
    name: string;
    description?: string;
    price?: number;
    price_formatted?: string;
    image_url?: string;
    video_url?: string;
    category?: string;
    tags?: string[];
}

export interface ProductSlideshowProps {
    items: SlideshowItem[];
    autoPlay?: boolean;
    autoPlayInterval?: number;
    showControls?: boolean;
    showIndicators?: boolean;
    showThumbnails?: boolean;
    enableZoom?: boolean;
    enableCategoryFilter?: boolean;
    className?: string;
    onItemClick?: (item: SlideshowItem) => void;
    onItemHover?: (item: SlideshowItem | null) => void;
    placeholderText?: string;
}

const formatPrice = (price: number): string => {
    if (!price) return '';
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        minimumFractionDigits: 0
    }).format(price);
};

const SLIDESHOW_CONFIG = {
    AUTO_PLAY_INTERVAL: 4000,
    TRANSITION_DURATION: 500,
    ZOOM_SCALE: 1.3,
    THUMBNAIL_WIDTH: 80,
    MIN_IMAGES_FOR_AUTO_PLAY: 2,
};

export const ProductSlideshow: React.FC<ProductSlideshowProps> = ({
    items,
    autoPlay = true,
    autoPlayInterval = SLIDESHOW_CONFIG.AUTO_PLAY_INTERVAL,
    showControls = true,
    showIndicators = true,
    showThumbnails = true,
    enableZoom = true,
    enableCategoryFilter = true,
    className,
    onItemClick,
    onItemHover,
    placeholderText = 'Chưa có hình ảnh sản phẩm',
}) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(autoPlay);
    const [isZoomed, setIsZoomed] = useState(false);
    const [isTransitioning, setIsTransitioning] = useState(false);
    const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set());
    const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
    const [showFullscreen, setShowFullscreen] = useState(false);
    const [direction, setDirection] = useState<'next' | 'prev'>('next');
    const containerRef = useRef<HTMLDivElement>(null);
    const timerRef = useRef<number | null>(null);
    const touchStartX = useRef<number>(0);
    const touchEndX = useRef<number>(0);

    const categories = useMemo(() => {
        const cats = new Set<string>();
        items.forEach(item => {
            if (item.category) cats.add(item.category);
        });
        return Array.from(cats).sort();
    }, [items]);

    const filteredItems = useMemo(() => {
        if (!selectedCategory) return items;
        return items.filter(item => item.category === selectedCategory);
    }, [items, selectedCategory]);

    const visibleItems = filteredItems.length > 0 ? filteredItems : items;
    const canAutoPlay = visibleItems.length >= SLIDESHOW_CONFIG.MIN_IMAGES_FOR_AUTO_PLAY;

    const goToSlide = useCallback((index: number, dir: 'next' | 'prev' = 'next') => {
        if (isTransitioning) return;
        
        setDirection(dir);
        setIsTransitioning(true);
        const newIndex = ((index % visibleItems.length) + visibleItems.length) % visibleItems.length;
        setCurrentIndex(newIndex);
        
        setTimeout(() => setIsTransitioning(false), SLIDESHOW_CONFIG.TRANSITION_DURATION);
    }, [isTransitioning, visibleItems.length]);

    const goNext = useCallback(() => {
        if (visibleItems.length <= 1) return;
        goToSlide(currentIndex + 1, 'next');
    }, [currentIndex, goToSlide, visibleItems.length]);

    const goPrev = useCallback(() => {
        if (visibleItems.length <= 1) return;
        goToSlide(currentIndex - 1, 'prev');
    }, [currentIndex, goToSlide, visibleItems.length]);

    const togglePlayPause = useCallback(() => {
        setIsPlaying(prev => !prev);
    }, []);

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        switch (e.key) {
            case 'ArrowLeft':
                goPrev();
                break;
            case 'ArrowRight':
                goNext();
                break;
            case ' ':
                e.preventDefault();
                togglePlayPause();
                break;
            case 'Escape':
                setShowFullscreen(false);
                break;
        }
    }, [goNext, goPrev, togglePlayPause]);

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);

    useEffect(() => {
        if (isPlaying && canAutoPlay && !showFullscreen) {
            timerRef.current = window.setInterval(goNext, autoPlayInterval);
        } else if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
        }
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [isPlaying, canAutoPlay, autoPlayInterval, goNext, showFullscreen]);

    useEffect(() => {
        setCurrentIndex(0);
    }, [selectedCategory]);

    const handleImageLoad = useCallback((itemId: string) => {
        setLoadedImages(prev => new Set(prev).add(itemId));
    }, []);

    const handleTouchStart = useCallback((e: React.TouchEvent) => {
        touchStartX.current = e.touches[0].clientX;
    }, []);

    const handleTouchMove = useCallback((e: React.TouchEvent) => {
        touchEndX.current = e.touches[0].clientX;
    }, []);

    const handleTouchEnd = useCallback(() => {
        const diff = touchStartX.current - touchEndX.current;
        if (Math.abs(diff) > 50) {
            if (diff > 0) goNext();
            else goPrev();
        }
    }, [goNext, goPrev]);

    const currentItem = visibleItems[currentIndex];
    const hasImages = visibleItems.some(item => item.image_url);
    const isVideo = currentItem?.video_url && !currentItem?.image_url;

    if (!hasImages && visibleItems.length === 0) {
        return (
            <div className={clsx('slideshow-placeholder', className)}>
                <div className="slideshow-placeholder-content">
                    <ImageIcon className="slideshow-placeholder-icon" />
                    <p className="slideshow-placeholder-text">{placeholderText}</p>
                </div>
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className={clsx(
                'product-slideshow',
                isTransitioning && 'is-transitioning',
                showFullscreen && 'is-fullscreen',
                className
            )}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
        >
            {/* Category Filter */}
            {enableCategoryFilter && categories.length > 1 && (
                <div className="slideshow-category-filter">
                    <div className="slideshow-category-dropdown">
                        <select
                            value={selectedCategory || ''}
                            onChange={(e) => setSelectedCategory(e.target.value || null)}
                            className="slideshow-category-select"
                        >
                            <option value="">Tất cả danh mục</option>
                            {categories.map(cat => (
                                <option key={cat} value={cat}>{cat}</option>
                            ))}
                        </select>
                        <ChevronDown className="slideshow-category-icon" />
                    </div>
                </div>
            )}

            {/* Main Slideshow Area */}
            <div 
                className="slideshow-main"
                onClick={() => onItemClick?.(currentItem)}
            >
                {/* Slide Content */}
                <div
                    className={clsx(
                        'slideshow-slide',
                        direction === 'next' ? 'slide-enter-right' : 'slide-enter-left'
                    )}
                >
                    {isVideo ? (
                        <video
                            key={currentItem?.id}
                            src={currentItem?.video_url}
                            className="slideshow-media slideshow-video"
                            controls
                            autoPlay={isPlaying}
                            muted={false}
                        />
                    ) : (
                        <div 
                            className={clsx('slideshow-image-container', isZoomed && 'is-zoomed')}
                            onMouseEnter={() => {
                                if (enableZoom) setIsZoomed(true);
                                onItemHover?.(currentItem);
                            }}
                            onMouseLeave={() => {
                                setIsZoomed(false);
                                onItemHover?.(null);
                            }}
                        >
                            {currentItem?.image_url ? (
                                <>
                                    {!loadedImages.has(currentItem.id) && (
                                        <div className="slideshow-loading">
                                            <Loader2 className="slideshow-spinner" />
                                        </div>
                                    )}
                                    <img
                                        key={currentItem?.id}
                                        src={currentItem?.image_url}
                                        alt={currentItem?.name}
                                        className={clsx(
                                            'slideshow-image',
                                            loadedImages.has(currentItem.id) && 'is-loaded'
                                        )}
                                        onLoad={() => handleImageLoad(currentItem?.id)}
                                        loading="lazy"
                                        style={isZoomed ? { transform: `scale(${SLIDESHOW_CONFIG.ZOOM_SCALE})` } : undefined}
                                    />
                                    {enableZoom && (
                                        <div className="slideshow-zoom-indicator">
                                            <ZoomIn size={16} />
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="slideshow-no-image">
                                    <ImageIcon size={48} />
                                    <span>Chưa có hình</span>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Product Info Overlay */}
                {currentItem && (
                    <div className="slideshow-info-overlay">
                        <div className="slideshow-product-name">{currentItem.name}</div>
                        {currentItem.price !== undefined && (
                            <div className="slideshow-product-price">
                                {currentItem.price_formatted || formatPrice(currentItem.price)}
                            </div>
                        )}
                        {currentItem.description && (
                            <div className="slideshow-product-description">
                                {currentItem.description}
                            </div>
                        )}
                    </div>
                )}

                {/* Controls */}
                {showControls && visibleItems.length > 1 && (
                    <>
                        <button
                            className="slideshow-nav slideshow-nav-prev"
                            onClick={(e) => { e.stopPropagation(); goPrev(); }}
                            aria-label="Previous slide"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        <button
                            className="slideshow-nav slideshow-nav-next"
                            onClick={(e) => { e.stopPropagation(); goNext(); }}
                            aria-label="Next slide"
                        >
                            <ChevronRight size={24} />
                        </button>
                        <button
                            className="slideshow-play-pause"
                            onClick={(e) => { e.stopPropagation(); togglePlayPause(); }}
                            aria-label={isPlaying ? 'Pause' : 'Play'}
                        >
                            {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                        </button>
                    </>
                )}

                {/* Indicators */}
                {showIndicators && visibleItems.length > 1 && (
                    <div className="slideshow-indicators">
                        {visibleItems.map((_, idx) => (
                            <button
                                key={idx}
                                className={clsx('slideshow-indicator', idx === currentIndex && 'is-active')}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    goToSlide(idx, idx > currentIndex ? 'next' : 'prev');
                                }}
                                aria-label={`Go to slide ${idx + 1}`}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Thumbnails */}
            {showThumbnails && visibleItems.length > 1 && (
                <div className="slideshow-thumbnails">
                    {visibleItems.map((item, idx) => (
                        <button
                            key={item.id}
                            className={clsx('slideshow-thumbnail', idx === currentIndex && 'is-active')}
                            onClick={(e) => {
                                e.stopPropagation();
                                goToSlide(idx, idx > currentIndex ? 'next' : 'prev');
                            }}
                        >
                            {item.image_url ? (
                                <img
                                    src={item.image_url}
                                    alt={item.name}
                                    loading="lazy"
                                />
                            ) : (
                                <div className="slideshow-thumbnail-placeholder">
                                    <ImageIcon size={16} />
                                </div>
                            )}
                            {item.video_url && (
                                <div className="slideshow-thumbnail-video-indicator">
                                    <Film size={12} />
                                </div>
                            )}
                        </button>
                    ))}
                </div>
            )}

            {/* Fullscreen Button */}
            {enableZoom && (
                <button
                    className="slideshow-fullscreen-btn"
                    onClick={(e) => { e.stopPropagation(); setShowFullscreen(true); }}
                    aria-label="Fullscreen"
                >
                    <ZoomIn size={18} />
                </button>
            )}

            {/* Fullscreen Modal */}
            {showFullscreen && (
                <div className="slideshow-fullscreen-modal" onClick={() => setShowFullscreen(false)}>
                    <button
                        className="slideshow-fullscreen-close"
                        onClick={() => setShowFullscreen(false)}
                        aria-label="Close fullscreen"
                    >
                        <X size={24} />
                    </button>
                    <div className="slideshow-fullscreen-content" onClick={(e) => e.stopPropagation()}>
                        {currentItem?.image_url && (
                            <img
                                src={currentItem.image_url}
                                alt={currentItem.name}
                                className="slideshow-fullscreen-image"
                            />
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProductSlideshow;
