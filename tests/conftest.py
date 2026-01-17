import sys
from dataclasses import dataclass
from types import ModuleType

from pydantic import BaseModel


def _install_erc3_stub() -> None:
    if "erc3" in sys.modules:
        return

    class StoreRequest(BaseModel):
        model_config = {"extra": "forbid"}

    class Req_ListProducts(StoreRequest):
        limit: int = 5
        offset: int = 0

    class Req_ViewBasket(StoreRequest):
        pass

    class Req_ApplyCoupon(StoreRequest):
        coupon_code: str = ""

    class Req_RemoveCoupon(StoreRequest):
        pass

    class Req_AddProductToBasket(StoreRequest):
        sku: str = ""
        quantity: int = 1

    class Req_RemoveItemFromBasket(StoreRequest):
        item_id: str = ""

    class Req_CheckoutBasket(StoreRequest):
        pass

    store_module = ModuleType("erc3.store")
    store_module.Req_ListProducts = Req_ListProducts
    store_module.Req_ViewBasket = Req_ViewBasket
    store_module.Req_ApplyCoupon = Req_ApplyCoupon
    store_module.Req_RemoveCoupon = Req_RemoveCoupon
    store_module.Req_AddProductToBasket = Req_AddProductToBasket
    store_module.Req_RemoveItemFromBasket = Req_RemoveItemFromBasket
    store_module.Req_CheckoutBasket = Req_CheckoutBasket

    @dataclass
    class TaskInfo:
        task_id: str
        task_text: str

    class ERC3:
        pass

    module = ModuleType("erc3")
    module.store = store_module
    module.TaskInfo = TaskInfo
    module.ERC3 = ERC3

    sys.modules["erc3"] = module
    sys.modules["erc3.store"] = store_module


_install_erc3_stub()
