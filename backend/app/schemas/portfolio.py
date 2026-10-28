"""Portfolio update request and response."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortfolioUpdateRequest(BaseModel):
    """New portfolio name. The service rejects a blank name."""

    name: str


class PortfolioResponse(BaseModel):
    """Portfolio after a successful rename."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    created_at: datetime
