import os
import csv
from collections import defaultdict
from typing import List
from src.config import DATA_DIR

class DataLoader:
    def __init__(self):
        self.orders_by_id = {}
        self.orders_by_customer = {}
        self.customers_by_id = {}
        self.customer_orders_map = defaultdict(list)
        self.items_by_order = defaultdict(list)
        self.payments_by_order = defaultdict(list)
        self.products_by_id = {}

        self._load_data()

    def _load_csv(self, filename: str) -> List[dict]:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File not found {filepath}")
            return []
        
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _load_data(self):
        # 1. Orders
        orders = self._load_csv("olist_orders_dataset.csv")
        for row in orders:
            order_id = row['order_id']
            customer_id = row['customer_id']
            self.orders_by_id[order_id] = row
            self.orders_by_customer[customer_id] = order_id
            
        # 2. Customers
        customers = self._load_csv("olist_customers_dataset.csv")
        for row in customers:
            customer_id = row['customer_id']
            customer_unique_id = row['customer_unique_id']
            self.customers_by_id[customer_id] = customer_unique_id
            
        # Build customer_orders_map
        for customer_id, order_id in self.orders_by_customer.items():
            if customer_id in self.customers_by_id:
                unique_id = self.customers_by_id[customer_id]
                self.customer_orders_map[unique_id].append(order_id)

        # 3. Items
        items = self._load_csv("olist_order_items_dataset.csv")
        for row in items:
            self.items_by_order[row['order_id']].append(row)

        # 4. Payments
        payments = self._load_csv("olist_order_payments_dataset.csv")
        for row in payments:
            self.payments_by_order[row['order_id']].append(row)

        # 5. Products
        products = self._load_csv("olist_products_dataset.csv")
        for row in products:
            self.products_by_id[row['product_id']] = row

        # 6. Category Translation
        self.category_translation = {}
        translations = self._load_csv("product_category_name_translation.csv")
        for row in translations:
            self.category_translation[row['product_category_name']] = row['product_category_name_english']

    def get_order(self, order_id: str) -> dict:
        return self.orders_by_id.get(order_id, {})

    def get_customer_id_by_order(self, order_id: str) -> str:
        order = self.get_order(order_id)
        return order.get('customer_id', '')

    def get_customer_unique_id(self, customer_id: str) -> str:
        return self.customers_by_id.get(customer_id, '')

    def get_customer_history(self, customer_unique_id: str, exclude_order_id: str) -> List[str]:
        all_orders = self.customer_orders_map.get(customer_unique_id, [])
        return [oid for oid in all_orders if oid != exclude_order_id]

    def get_order_items(self, order_id: str) -> List[dict]:
        return self.items_by_order.get(order_id, [])

    def get_order_payments(self, order_id: str) -> List[dict]:
        return self.payments_by_order.get(order_id, [])

    def get_product(self, product_id: str) -> dict:
        return self.products_by_id.get(product_id, {})

    def translate_category(self, category_pt: str) -> str:
        """Translate Portuguese product category name to English."""
        if not category_pt:
            return ""
        return self.category_translation.get(category_pt, category_pt)
