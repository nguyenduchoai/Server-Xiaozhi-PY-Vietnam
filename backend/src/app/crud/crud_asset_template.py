"""
Asset Template CRUD Operations
"""

from fastcrud import FastCRUD

from app.models.asset_template import AssetTemplate
from app.schemas.asset_template import AssetTemplateCreate, AssetTemplateUpdate, AssetTemplateRead

crud_asset_template = FastCRUD[AssetTemplate, AssetTemplateCreate, AssetTemplateUpdate, AssetTemplateUpdate, None, AssetTemplateRead](AssetTemplate)
