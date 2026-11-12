from fastapi import APIRouter

from app.api.routes.account import router as account_router
from app.api.routes.brokerage_credentials import router as brokerage_credentials_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.market_data import router as market_data_router
from app.api.routes.onboarding import router as onboarding_router
from app.api.routes.optimization_runs import router as optimization_runs_router
from app.api.routes.optimizations import router as optimizations_router
from app.api.routes.portfolios import router as portfolios_router
from app.api.routes.stocks import router as stocks_router
from app.api.routes.trade import router as trade_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(account_router)
api_router.include_router(brokerage_credentials_router)
api_router.include_router(chat_router)
api_router.include_router(stocks_router)
api_router.include_router(market_data_router)
api_router.include_router(optimizations_router)
api_router.include_router(portfolios_router)
api_router.include_router(optimization_runs_router)
api_router.include_router(onboarding_router)
api_router.include_router(trade_router)
