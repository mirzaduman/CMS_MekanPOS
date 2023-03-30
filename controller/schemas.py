from ninja import Schema
from typing import List


class CreateDevice(Schema):
    token: str


class NotificationTest(Schema):
    token: str
    title: str
    body: str


class Login(Schema):
    key: str
    username: str
    password: str
    token: str


class GetTables(Schema):
    key: str
    user_id: int


class GetTable(Schema):
    key: str
    user_id: int
    table_id: int


class GetProducts(Schema):
    key: str
    table_id: int


class GetProduct(Schema):
    key: str
    table_id: int
    product_id: int


class GetBasket(Schema):
    key: str
    table_id: int


class GetOrder(Schema):
    key: str
    order_id: int


class RemoveOrderFromBasket(Schema):
    key: str
    order_id: int


class AddOrder(Schema):
    key: str
    user_id: int
    table_id: int
    product_id: int
    amount: int
    additional_info: str = None
    extras: List[str] = None
    additional_extras: List[str] = None
    good_withs: List[str] = None
    gang: int


class GetEditOrder(Schema):
    key: str
    order_id: int


class PostEditOrder(Schema):
    key: str
    user_id: int
    order_id: int
    amount: int = None
    additional_info: str = None
    extras: List[str] = None
    additional_extras: List[str] = None
    gang: int = None


class SendBasket(Schema):
    key: str
    user_id: int
    table_id: int
    orders: str = None


class GetNotifications(Schema):
    key: str
    user_id: int


class AcceptWaiterCall(Schema):
    key: str
    notification_id: int


class GetApproveBasket(Schema):
    key: str
    basket_id: int


class ApproveBasket(Schema):
    key: str
    user_id: int
    basket_id: int


class DeclineBasket(Schema):
    key: str
    user_id: int
    basket_id: int


class SpamBasket(Schema):
    key: str
    user_id: int
    basket_id: int


class GetWorkersTables(Schema):
    key: str
    user_id: int


class ResetAllTables(Schema):
    key: str
    user_id: int


class GetWorkerTables(Schema):
    key: str
    user_id: int
    waiter_id: int


class AssignTables(Schema):
    key: str
    user_id: int
    waiter_id: int
    tables: List[str]


class GetTablesIds(Schema):
    key: str
    user_id: int


class ChangeSessionTable(Schema):
    key: str
    user_id: int
    session_id: int
    table_id: int


class DeleteOrdersOfBasket(Schema):
    key: str
    user_id: int
    basket_id: int


class ChangeOrderTable(Schema):
    key: str
    user_id: int
    order_id: int
    table_id: int


class DeleteOrder(Schema):
    key: str
    user_id: int
    order_id: int


class GetWorkers(Schema):
    key: str
    user_id: int


class DeleteWorker(Schema):
    key: str
    user_id: int
    worker_id: int


class AddWorker(Schema):
    key: str
    user_id: int
    worker_name: str
    role: str
    phone: str = None
    username: str


class GetCreateProductData(Schema):
    key: str
    user_id: int


class CreateProduct(Schema):
    key: str
    user_id: int
    name_de: str
    name_tr: str
    name_en: str
    product_nr: str = None
    category_id: int
    price: float
    allergens: List[str] = None
    extras: str = None
    description_de: str = None
    description_tr: str = None
    description_en: str = None
    good_with: List[str] = None
    content_disclaimers: List[str] = None
    product_status: int


class AddExtraToProduct(Schema):
    key: str
    user_id: int
    product_id: int
    name_de: str
    name_tr: str
    name_en: str
    price: float


class GetEditProduct(Schema):
    key: str
    user_id: int
    product_id: int


class EditProduct(Schema):
    key: str
    user_id: str
    product_id: int
    name_de: str = None
    name_tr: str = None
    name_en: str = None
    product_nr: str = None
    category_id: int = None
    price: float = None
    allergens: List[str] = None
    description_de: str = None
    description_tr: str = None
    description_en: str = None
    good_with: List[str] = None
    content_disclaimers: List[str] = None
    product_status: int = None
    extras: str = None


class EditExtra(Schema):
    key: str
    user_id: int
    extra_id: int
    name_de: str = None
    name_tr: str = None
    name_en: str = None
    price: float = None


class DeleteExtra(Schema):
    key: str
    user_id: int
    extra_id: int


class GetAreas(Schema):
    key: str
    user_id: int


class GetAreaTables(Schema):
    key: str
    user_id: int
    area_id: int


class ChangeTableArea(Schema):
    key: str
    user_id: int
    table_id: int
    area_id: int


class CreateTable(Schema):
    key: str
    user_id: int
    area_id: int
    table_nr: str


class EditTable(Schema):
    key: str
    user_id: int
    table_id: int
    area: int


class DeleteTable(Schema):
    key: str
    user_id: int
    table_id: int


class GetChangeAreaTables(Schema):
    key: str
    user_id: int
    area_id: int


class ChangeAreaTables(Schema):
    key: str
    user_id: int
    area_id: int
    tables: List[str]
    name: str = None


class CreateArea(Schema):
    key: str
    user_id: int
    area_name: str
    tables: List[str] = None


class DeleteArea(Schema):
    key: str
    area_id: int


class GetSession(Schema):
    key: str
    table_id: int


class MakePayment(Schema):
    key: str
    session_id: int
    payment_method: str
    orders: List[str]


class GetBaskets(Schema):
    key: str


class FinishBasket(Schema):
    key: str
    basket_id: int


class GetProductsManager(Schema):
    key: str
    user_id: int
