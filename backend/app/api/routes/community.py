"""Signed-in Community forum routes."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.current_user import CommunityPrincipal, get_community_principal
from app.core.db import get_db
from app.repositories.community_repository import CommunityRepository
from app.schemas.community import CategoryResponse, Page, PostCreate, PostResponse, PostUpdate, ReplyCreate, ReplyResponse, ReplyUpdate
from app.services.community_service import CommunityService

router = APIRouter(prefix="/community", tags=["community"])


def get_community_service(
    db: Session = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
) -> CommunityService:
    return CommunityService(CommunityRepository(db), settings.community_page_size, settings.community_page_max)


@router.get("/categories", response_model=list[CategoryResponse])
def categories(
    _principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> list[CategoryResponse]:
    return service.categories()


@router.post("/posts", response_model=PostResponse, status_code=201)
def create_post(
    body: PostCreate,
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> PostResponse:
    return service.create_post(principal, body)


@router.get("/posts", response_model=Page[PostResponse])
def list_posts(
    category: Literal["question", "discussion", "portfolio"] | None = None,
    cursor: str | None = None,
    limit: int | None = Query(default=None),
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> Page[PostResponse]:
    return service.list_posts(category, cursor, limit, principal.user_id)


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: uuid.UUID,
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> PostResponse:
    return service.get_post(post_id, principal.user_id)


@router.patch("/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: uuid.UUID,
    body: PostUpdate,
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> PostResponse:
    return service.update_post(post_id, principal, body)


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: uuid.UUID,
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> Response:
    service.delete_post(post_id, principal)
    return Response(status_code=204)


@router.get("/posts/{post_id}/replies", response_model=Page[ReplyResponse])
def list_replies(
    post_id: uuid.UUID,
    parent_reply_id: uuid.UUID | None = None,
    cursor: str | None = None,
    limit: int | None = Query(default=None),
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> Page[ReplyResponse]:
    return service.list_replies(post_id, parent_reply_id, cursor, limit, principal.user_id)


@router.post("/posts/{post_id}/replies", response_model=ReplyResponse, status_code=201)
def create_reply(
    post_id: uuid.UUID,
    body: ReplyCreate,
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> ReplyResponse:
    return service.create_reply(post_id, principal, body)


@router.patch("/posts/{post_id}/replies/{reply_id}", response_model=ReplyResponse)
def update_reply(
    post_id: uuid.UUID,
    reply_id: uuid.UUID,
    body: ReplyUpdate,
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> ReplyResponse:
    return service.update_reply(post_id, reply_id, principal, body)


@router.delete("/posts/{post_id}/replies/{reply_id}", status_code=204)
def delete_reply(
    post_id: uuid.UUID,
    reply_id: uuid.UUID,
    principal: CommunityPrincipal = Depends(get_community_principal),
    service: CommunityService = Depends(get_community_service),
) -> Response:
    service.delete_reply(post_id, reply_id, principal)
    return Response(status_code=204)
