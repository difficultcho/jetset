from fastapi import APIRouter, Depends

from app.api.admin import auth, banners, coupons, orders, products, stats, users, wholesale
from app.deps import get_current_admin

admin_router = APIRouter()
admin_router.include_router(auth.router, tags=["管理-认证"])

protected = APIRouter(dependencies=[Depends(get_current_admin)])
protected.include_router(products.router, tags=["管理-商品"])
protected.include_router(orders.router, tags=["管理-订单"])
protected.include_router(wholesale.router, tags=["管理-批发审核"])
protected.include_router(banners.router, tags=["管理-运营位"])
protected.include_router(coupons.router, tags=["管理-优惠券"])
protected.include_router(users.router, tags=["管理-用户"])
protected.include_router(stats.router, tags=["管理-统计"])
admin_router.include_router(protected)
