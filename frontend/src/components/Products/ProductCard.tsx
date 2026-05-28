/**
 * Product Card Display - Template cho hiển thị sản phẩm
 * 
 * Dùng cho:
 * - Kiosk Mode
 * - Device Screen Push
 * - Voice Assistant Response
 */

import React from 'react';
import { Card, Typography, Tag, Space, Image, Button, Rating } from '@douyinfe/semi-ui';
import { IconShoppingBag, IconPlay } from '@douyinfe/semi-icons';
import './ProductCard.css';

const { Title, Text, Paragraph } = Typography;

export interface ProductCardData {
    id: string;
    name: string;
    description: string;
    price: number;
    price_formatted?: string;
    image_url?: string;
    video_url?: string;
    category?: string;
    in_stock?: boolean;
    rating?: number;
    tags?: string[];
}

export interface ProductCardProps {
    product: ProductCardData;
    variant?: 'default' | 'compact' | 'large' | 'horizontal';
    showPrice?: boolean;
    showDescription?: boolean;
    showActions?: boolean;
    onClick?: (product: ProductCardData) => void;
    onAddToCart?: (product: ProductCardData) => void;
    onPlayVideo?: (product: ProductCardData) => void;
}

/**
 * Format price to Vietnamese currency
 */
const formatPrice = (price: number): string => {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        minimumFractionDigits: 0
    }).format(price);
};

/**
 * Default Product Card - Vertical layout
 */
const ProductCard: React.FC<ProductCardProps> = ({
    product,
    variant = 'default',
    showPrice = true,
    showDescription = true,
    showActions = false,
    onClick,
    onAddToCart,
    onPlayVideo
}) => {
    const handleClick = () => {
        if (onClick) onClick(product);
    };

    const priceDisplay = product.price_formatted || formatPrice(product.price);

    // Compact variant
    if (variant === 'compact') {
        return (
            <div className="clickable-card" onClick={handleClick} role="button" tabIndex={0}>
                <Card
                    className="product-card product-card-compact"
                    shadows="hover"
                    cover={
                        product.image_url ? (
                            <img
                                src={product.image_url}
                                alt={product.name}
                                style={{ height: 100, objectFit: 'cover', width: '100%' }}
                            />
                        ) : null
                    }
                >
                    <Text strong ellipsis={{ showTooltip: true }}>{product.name}</Text>
                    {showPrice && (
                        <Text type="danger" strong>{priceDisplay}</Text>
                    )}
                </Card>
            </div>
        );
    }

    // Large variant
    if (variant === 'large') {
        return (
            <div className="clickable-card" onClick={handleClick} role="button" tabIndex={0}>
                <Card className="product-card product-card-large">
                    <div className="product-card-large-content">
                        {product.image_url && (
                            <div className="product-image-large">
                                <Image
                                    src={product.image_url}
                                    alt={product.name}
                                    width="100%"
                                    style={{ maxHeight: 400, objectFit: 'contain' }}
                                />
                                {product.video_url && (
                                    <Button
                                        theme="solid"
                                        type="primary"
                                        icon={<IconPlay />}
                                        size="large"
                                        className="video-play-button"
                                        onClick={(e: React.MouseEvent) => {
                                            e.stopPropagation();
                                            if (onPlayVideo) onPlayVideo(product);
                                        }}
                                    />
                                )}
                            </div>
                        )}

                        <Space vertical spacing="medium" style={{ width: '100%' }}>
                            <Title heading={2}>{product.name}</Title>

                            {product.category && (
                                <Tag color="blue">{product.category}</Tag>
                            )}

                            {showPrice && (
                                <Title heading={1} type="danger" style={{ margin: 0 }}>
                                    {priceDisplay}
                                </Title>
                            )}

                            {product.rating !== undefined && product.rating > 0 && (
                                <Rating disabled defaultValue={product.rating} allowHalf />
                            )}

                            {showDescription && product.description && (
                                <Paragraph>{product.description}</Paragraph>
                            )}

                            {product.tags && product.tags.length > 0 && (
                                <Space wrap>
                                    {product.tags.map((tag, i) => (
                                        <Tag key={i}>{tag}</Tag>
                                    ))}
                                </Space>
                            )}

                            {showActions && (
                                <Space>
                                    <Button
                                        theme="solid"
                                        size="large"
                                        icon={<IconShoppingBag />}
                                        disabled={!product.in_stock}
                                        onClick={(e: React.MouseEvent) => {
                                            e.stopPropagation();
                                            if (onAddToCart) onAddToCart(product);
                                        }}
                                    >
                                        {product.in_stock ? 'Thêm vào giỏ' : 'Hết hàng'}
                                    </Button>
                                </Space>
                            )}
                        </Space>
                    </div>
                </Card>
            </div>
        );
    }

    // Horizontal variant
    if (variant === 'horizontal') {
        return (
            <div className="clickable-card" onClick={handleClick} role="button" tabIndex={0}>
                <Card className="product-card product-card-horizontal" shadows="hover">
                    <div className="product-horizontal-layout">
                        {product.image_url && (
                            <img
                                src={product.image_url}
                                alt={product.name}
                                style={{ width: 150, height: 150, objectFit: 'cover', borderRadius: 8 }}
                            />
                        )}
                        <div className="product-horizontal-info">
                            <Title heading={4} ellipsis={{ rows: 2 }}>{product.name}</Title>
                            {product.category && (
                                <Tag color="blue" style={{ marginBottom: 8 }}>{product.category}</Tag>
                            )}
                            {showDescription && (
                                <Paragraph ellipsis={{ rows: 2 }} type="tertiary">
                                    {product.description}
                                </Paragraph>
                            )}
                            <Space>
                                {showPrice && (
                                    <Text type="danger" strong style={{ fontSize: 18 }}>
                                        {priceDisplay}
                                    </Text>
                                )}
                                {product.rating !== undefined && product.rating > 0 && (
                                    <Text type="tertiary">⭐ {product.rating.toFixed(1)}</Text>
                                )}
                            </Space>
                        </div>
                    </div>
                </Card>
            </div>
        );
    }

    // Default variant
    return (
        <div className="clickable-card" onClick={handleClick} role="button" tabIndex={0}>
            <Card
                className="product-card product-card-default"
                shadows="hover"
                cover={
                    product.image_url ? (
                        <div className="product-image-container">
                            <img
                                src={product.image_url}
                                alt={product.name}
                                style={{ height: 200, objectFit: 'cover', width: '100%' }}
                            />
                            {!product.in_stock && (
                                <div className="out-of-stock-overlay">
                                    <Text strong style={{ color: 'white' }}>Hết hàng</Text>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="product-placeholder-default">
                            <IconShoppingBag style={{ fontSize: 48, opacity: 0.5 }} />
                        </div>
                    )
                }
            >
                <Card.Meta
                    title={<Text ellipsis={{ showTooltip: true }}>{product.name}</Text>}
                    description={
                        <Space vertical spacing={4} style={{ width: '100%' }}>
                            {product.category && (
                                <Tag color="blue" size="small">{product.category}</Tag>
                            )}
                            {showPrice && (
                                <Text type="danger" strong style={{ fontSize: 16 }}>
                                    {priceDisplay}
                                </Text>
                            )}
                            {product.rating !== undefined && product.rating > 0 && (
                                <Text type="tertiary">⭐ {product.rating.toFixed(1)}</Text>
                            )}
                        </Space>
                    }
                />
            </Card>
        </div>
    );
};

export default ProductCard;
