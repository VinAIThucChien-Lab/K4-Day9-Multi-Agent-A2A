import os
import pandas as pd
from typing import Dict, List, Optional, Any
from src.config import DATA_DIR

class DataLoader:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        
        self.orders_by_id: Dict[str, Dict[str, Any]] = {}
        self.orders_by_customer: Dict[str, str] = {}
        self.customers_by_id: Dict[str, str] = {}
        self.customer_orders_map: Dict[str, List[str]] = {}
        self.items_by_order: Dict[str, List[Dict[str, Any]]] = {}
        self.payments_by_order: Dict[str, List[Dict[str, Any]]] = {}
        self.products_by_id: Dict[str, Dict[str, Any]] = {}
        self.category_translation: Dict[str, str] = {}
        
        self._load_data()
        
    def _load_data(self):
        # 1. Orders
        orders_path = os.path.join(self.data_dir, "olist_orders_dataset.csv")
        if os.path.exists(orders_path):
            df_orders = pd.read_csv(orders_path, dtype=str)
            for _, row in df_orders.iterrows():
                row_dict = row.dropna().to_dict()
                order_id = row_dict.get("order_id")
                customer_id = row_dict.get("customer_id")
                if order_id:
                    self.orders_by_id[order_id] = row_dict
                    if customer_id:
                        self.orders_by_customer[customer_id] = order_id

        # 2. Customers
        customers_path = os.path.join(self.data_dir, "olist_customers_dataset.csv")
        if os.path.exists(customers_path):
            df_cust = pd.read_csv(customers_path, dtype=str)
            for _, row in df_cust.iterrows():
                row_dict = row.dropna().to_dict()
                cid = row_dict.get("customer_id")
                c_unique_id = row_dict.get("customer_unique_id")
                if cid and c_unique_id:
                    self.customers_by_id[cid] = c_unique_id
                    order_id = self.orders_by_customer.get(cid)
                    if order_id:
                        if c_unique_id not in self.customer_orders_map:
                            self.customer_orders_map[c_unique_id] = []
                        self.customer_orders_map[c_unique_id].append(order_id)

        # 3. Order Items
        items_path = os.path.join(self.data_dir, "olist_order_items_dataset.csv")
        if os.path.exists(items_path):
            df_items = pd.read_csv(items_path, dtype=str)
            for _, row in df_items.iterrows():
                row_dict = row.dropna().to_dict()
                order_id = row_dict.get("order_id")
                if order_id:
                    if order_id not in self.items_by_order:
                        self.items_by_order[order_id] = []
                    self.items_by_order[order_id].append(row_dict)

        # 4. Order Payments
        payments_path = os.path.join(self.data_dir, "olist_order_payments_dataset.csv")
        if os.path.exists(payments_path):
            df_payments = pd.read_csv(payments_path, dtype=str)
            for _, row in df_payments.iterrows():
                row_dict = row.dropna().to_dict()
                order_id = row_dict.get("order_id")
                if order_id:
                    if order_id not in self.payments_by_order:
                        self.payments_by_order[order_id] = []
                    self.payments_by_order[order_id].append(row_dict)

        # 5. Products
        products_path = os.path.join(self.data_dir, "olist_products_dataset.csv")
        if os.path.exists(products_path):
            df_products = pd.read_csv(products_path, dtype=str)
            for _, row in df_products.iterrows():
                row_dict = row.dropna().to_dict()
                pid = row_dict.get("product_id")
                if pid:
                    self.products_by_id[pid] = row_dict

        # 6. Category Translation
        trans_path = os.path.join(self.data_dir, "product_category_name_translation.csv")
        if os.path.exists(trans_path):
            df_trans = pd.read_csv(trans_path, dtype=str)
            for _, row in df_trans.iterrows():
                pt = row.get("product_category_name")
                en = row.get("product_category_name_english")
                if pt and en:
                    self.category_translation[pt] = en

    def get_order(self, order_id: str) -> Dict[str, Any]:
        return self.orders_by_id.get(order_id, {})

    def get_customer_id_by_order(self, order_id: str) -> str:
        order = self.get_order(order_id)
        return order.get("customer_id", "")

    def get_customer_unique_id(self, customer_id: str) -> str:
        return self.customers_by_id.get(customer_id, "")

    def get_customer_history(self, customer_unique_id: str, exclude_order_id: str = "") -> List[str]:
        all_orders = self.customer_orders_map.get(customer_unique_id, [])
        return [oid for oid in all_orders if oid != exclude_order_id]

    def get_order_items(self, order_id: str) -> List[Dict[str, Any]]:
        return self.items_by_order.get(order_id, [])

    def get_order_payments(self, order_id: str) -> List[Dict[str, Any]]:
        return self.payments_by_order.get(order_id, [])

    def get_product(self, product_id: str) -> Dict[str, Any]:
        return self.products_by_id.get(product_id, {})

    def translate_category(self, category_pt: str) -> str:
        return self.category_translation.get(category_pt, category_pt)
