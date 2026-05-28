"""
Knowledge module - cung cấp công cụ quản lý cơ sở tri thức cho agent.

Sử dụng ChromaDB để lưu trữ và tìm kiếm tri thức.

Tool functions:
- search_knowledge_base: Tìm kiếm thông tin trong cơ sở tri thức ChromaDB
- add_knowledge: Thêm thông tin mới vào cơ sở tri thức

Features:
- Tìm kiếm semantic với vector embeddings
- Hỗ trợ Image URL cho khuyến nghị sản phẩm
- Import từ Google Sheets, CSV, URL

Ví dụ sử dụng:
    # Tìm kiếm tri thức
    search_knowledge_base(query="thông tin sản phẩm X", k=5, conn=conn)

    # Thêm tri thức mới
    add_knowledge(content="Thông tin sản phẩm", sector="semantic", conn=conn)
"""

# Import tool functions để đăng ký chúng
try:
    from app.ai.plugins_func.functions.knowledge.search_knowledge import (
        search_knowledge_base,
    )  # noqa: F401
    from app.ai.plugins_func.functions.knowledge.add_knowledge import (
        add_knowledge,
    )  # noqa: F401
except ImportError as e:
    import warnings

    warnings.warn(f"Failed to import knowledge tool functions: {e}")
    search_knowledge_base = None
    add_knowledge = None

__all__ = [
    "search_knowledge_base",
    "add_knowledge",
]
