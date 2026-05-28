"""
GraphQL Router Configuration

Provides GraphQL endpoint integration with FastAPI.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig

from .resolvers import schema


graphql_router = APIRouter(prefix="/graphql", tags=["GraphQL"])


async def get_context(request: Request) -> dict:
    """Get GraphQL context with request info."""
    return {
        "request": request,
        "user": getattr(request.state, "user", None),
    }


graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
    graphiql=True,
    path="/",
)


@graphql_router.get("/schema")
async def get_graphql_schema():
    """Get GraphQL schema in SDL format."""
    from strawberry.schema import print_schema
    
    return JSONResponse(
        content={"schema": print_schema(schema)},
        media_type="application/json",
    )
