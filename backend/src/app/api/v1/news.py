"""
News API Endpoints
REST API for news reading features.
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...api.dependencies import get_current_user
from ...core.logger import get_logger
from ...ai.plugins_func.functions.news import get_news_by_topic, get_news_detail
from ...ai.plugins_func.register import Action
from app.config import load_config
# NOTE: LLM provider is lazy-imported in /summarize endpoint to avoid boot crash
from app.core.config import settings

import json

router = APIRouter(tags=["news"], prefix="/news")
logger = get_logger(__name__)

# ==================== Schemas ====================

class NewsListRequest(BaseModel):
    """Request để lấy danh sách tin tức"""
    source: str = Field(default="vnexpress", description="Nguồn tin")
    topic: str = Field(default="", description="Chủ đề tin tức")
    max_articles: int = Field(default=10, ge=1, le=50, description="Số bài tối đa")

class ArticleDetailRequest(BaseModel):
    """Request để lấy chi tiết bài viết"""
    url: str = Field(..., description="URL của bài viết")
    source: str = Field(default="vnexpress", description="Nguồn tin")

class SummarizeRequest(BaseModel):
    """Request để tóm tắt bài viết"""
    url: str = Field(..., description="URL của bài viết")
    source: str = Field(default="vnexpress", description="Nguồn tin")

class NewsArticle(BaseModel):
    """Schema cho một bài viết tin tức"""
    index: int
    title: str
    description: Optional[str] = None
    link: str
    pub_date: Optional[str] = None
    image_url: Optional[str] = None

class NewsListResponse(BaseModel):
    """Response danh sách tin tức"""
    success: bool = True
    source: str
    topic: str
    total: int
    articles: list[NewsArticle]

class ArticleDetailResponse(BaseModel):
    """Response chi tiết bài viết"""
    success: bool = True
    title: str
    link: str
    content: str  # Markdown
    pub_date: Optional[str] = None
    source: str

class SummaryResponse(BaseModel):
    """Response tóm tắt"""
    success: bool = True
    article_url: str
    summary: str

class TopicInfo(BaseModel):
    """Thông tin về topic"""
    name: str
    path: str

class SourceInfo(BaseModel):
    """Thông tin về nguồn tin"""
    name: str
    base_url: str
    topics: list[TopicInfo]

# ==================== Mock Connection ====================

class MockConnection:
    """Mock connection object for tool calls"""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.selected_module_config = {}
    
    def load_config_from_db(self):
        """Load news config from settings"""
        # load_config imported at top-level
        load_config()
        # Return news config dict
        return {
            "news": {
                "default_source": "vnexpress",
                "max_articles": 10,
                "timeout": 10,
                "max_content_length": 4000,
                "sources": {
                    "vnexpress": {
                        "name": "VnExpress",
                        "type": "rss",
                        "base_url": "https://vnexpress.net/rss",
                        "topics": [
                            {"name": "Thời sự", "path": "/tin-moi-nhat.rss"},
                            {"name": "Thế giới", "path": "/the-gioi.rss"},
                            {"name": "Kinh doanh", "path": "/kinh-doanh.rss"},
                            {"name": "Giải trí", "path": "/giai-tri.rss"},
                            {"name": "Thể thao", "path": "/the-thao.rss"},
                            {"name": "Pháp luật", "path": "/phap-luat.rss"},
                            {"name": "Giáo dục", "path": "/giao-duc.rss"},
                            {"name": "Sức khỏe", "path": "/suc-khoe.rss"},
                            {"name": "Đời sống", "path": "/gia-dinh.rss"},
                            {"name": "Du lịch", "path": "/du-lich.rss"},
                            {"name": "Khoa học", "path": "/khoa-hoc.rss"},
                            {"name": "Số hóa", "path": "/so-hoa.rss"},
                            {"name": "Xe", "path": "/oto-xe-may.rss"},
                        ]
                    }
                }
            }
        }

# ==================== Endpoints ====================

@router.post("/list", response_model=NewsListResponse)
async def get_news_list(
    data: NewsListRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Lấy danh sách tin tức theo chủ đề.
    
    Returns JSON với articles array.
    """
    try:
        # Create mock connection
        conn = MockConnection(current_user["id"])
        
        # Call tool
        # json and Action imported at top-level
        
        result = await get_news_by_topic(
            conn=conn,
            source=data.source,
            topic=data.topic
        )
        
        if result.action == Action.REQLLM and result.result:
            # Parse JSON result
            result_data = json.loads(result.result)
            
            # If empty topic, return error
            if not data.topic:
                raise HTTPException(
                    status_code=400,
                    detail=f"Vui lòng chọn chủ đề. Có sẵn: {', '.join([t['name'] for t in result_data.get('topics', [])])}"
                )
            
            # Extract articles
            articles = result_data.get("articles", [])
            
            return NewsListResponse(
                source=result_data.get("source", data.source),
                topic=result_data.get("topic", data.topic),
                total=result_data.get("total", len(articles)),
                articles=[NewsArticle(**art) for art in articles]
            )
        else:
            raise HTTPException(status_code=500, detail="Không thể lấy tin tức")
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise HTTPException(status_code=500, detail="Lỗi parse response")
    except Exception as e:
        logger.error(f"Error in get_news_list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detail", response_model=ArticleDetailResponse)
async def get_article_detail(
    data: ArticleDetailRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Lấy nội dung chi tiết của bài viết.
    
    Returns markdown content.
    """
    try:
        # Create mock connection
        conn = MockConnection(current_user["id"])
        
        # Call tool
        # Action imported at top-level
        
        result = await get_news_detail(
            conn=conn,
            url=data.url,
            source=data.source
        )
        
        if result.action == Action.REQLLM and result.result:
            return ArticleDetailResponse(
                title=data.url.split("/")[-1],  # Extract from URL
                link=data.url,
                content=result.result,  # Already markdown
                source=data.source
            )
        else:
            raise HTTPException(status_code=500, detail="Không thể lấy nội dung bài viết")
            
    except Exception as e:
        logger.error(f"Error in get_article_detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize", response_model=SummaryResponse)
async def summarize_article(
    data: SummarizeRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """
    Tóm tắt bài viết bằng AI.
    
    Lấy nội dung bài viết rồi dùng LLM để tóm tắt.
    """
    try:
        # Create mock connection
        conn = MockConnection(current_user["id"])
        
        # Get article content first
        # Action imported at top-level
        
        content_result = await get_news_detail(
            conn=conn,
            url=data.url,
            source=data.source
        )
        
        if content_result.action != Action.REQLLM or not content_result.result:
            raise HTTPException(status_code=500, detail="Không thể lấy nội dung để tóm tắt")
        
        # Lazy import LLM provider to avoid boot crash (factory module doesn't exist)
        from app.ai.providers.llm.openai.openai import LLMProvider as OpenAILLMProvider
        
        llm = OpenAILLMProvider(
            model_name=getattr(settings, 'llm_model', 'gpt-4o-mini'),
            api_key=getattr(settings, 'llm_api_key', ''),
            base_url=getattr(settings, 'llm_base_url', None),
        )
        
        prompt = f"""Hãy tóm tắt bài viết dưới đây thành 3-5 câu ngắn gọn, súc tích:

{content_result.result[:2000]}

Tóm tắt:"""
        
        summary = await llm.generate_text(prompt)
        
        return SummaryResponse(
            article_url=data.url,
            summary=summary.strip()
        )
        
    except Exception as e:
        logger.error(f"Error in summarize_article: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_news_sources(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Lấy danh sách nguồn tin có sẵn"""
    try:
        conn = MockConnection(current_user["id"])
        config_dict = conn.load_config_from_db()
        news_config = config_dict.get("news", {})
        
        sources = []
        for source_name, source_data in news_config.get("sources", {}).items():
            topics = [
                TopicInfo(name=t["name"], path=t["path"])
                for t in source_data.get("topics", [])
            ]
            sources.append(SourceInfo(
                name=source_data.get("name", source_name),
                base_url=source_data.get("base_url", ""),
                topics=topics
            ))
        
        return {"success": True, "sources": sources}
        
    except Exception as e:
        logger.error(f"Error in get_news_sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_news_topics(
    source: str = "vnexpress",
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Lấy danh sách topics của một nguồn"""
    try:
        conn = MockConnection(current_user["id"])
        config_dict = conn.load_config_from_db()
        news_config = config_dict.get("news", {})
        
        source_data = news_config.get("sources", {}).get(source, {})
        topics = [
            TopicInfo(name=t["name"], path=t["path"])
            for t in source_data.get("topics", [])
        ]
        
        return {"success": True, "source": source, "topics": topics}
        
    except Exception as e:
        logger.error(f"Error in get_news_topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
