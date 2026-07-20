from fastapi import APIRouter

from app.api import (
    addresses, auth, brand, cart, catalog, coupons, home, me, orders, pages, payments,
    points, stores, uploads, wholesale,
)

api_router = APIRouter()
api_router.include_router(auth.router, tags=["认证"])
api_router.include_router(me.router, tags=["个人信息"])
api_router.include_router(coupons.router, tags=["优惠券"])
api_router.include_router(points.router, tags=["积分"])
api_router.include_router(home.router, tags=["首页"])
api_router.include_router(pages.router, tags=["配置化页面"])
api_router.include_router(catalog.router, tags=["商品"])
api_router.include_router(cart.router, tags=["购物车"])
api_router.include_router(addresses.router, tags=["收货地址"])
api_router.include_router(orders.router, tags=["订单"])
api_router.include_router(payments.router, tags=["支付"])
api_router.include_router(wholesale.router, tags=["批发合作"])
api_router.include_router(stores.router, tags=["门店"])
api_router.include_router(brand.router, tags=["品牌内容"])
api_router.include_router(uploads.router, tags=["上传"])
