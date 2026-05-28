from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from typing import Literal, Optional

class BannerConfig(BaseModel):
    url: str = Field(description="URL of the banner image")
    width: Optional[int] = Field(default=None, description="Width in pixels")
    height: Optional[int] = Field(default=None, description="Height in pixels")
    format: Optional[Literal["jpg", "jpeg", "png", "webp", "gif"]] = Field(default="jpg", description="Image format")
    duration: int = Field(default=5, ge=1, le=60, description="Display time in seconds")
    transition: Literal["fade", "slide", "zoom", "none"] = Field(default="none", description="Transition effect")
    scale_mode: Literal["contain", "cover", "stretch"] = Field(default="contain", description="Image scaling mode")
    alt_text: Optional[str] = Field(default=None, description="Alternative text")
    caption: Optional[str] = Field(default=None, description="Caption or text overlay")
    order_idx: int = Field(default=0, description="Display order index")
    
    model_config = ConfigDict(extra="ignore")
