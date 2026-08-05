from src.schemas import CaseContext, ProductContext
from src.data_loader import DataLoader

class OrderProductAgent:
    def process(self, context: CaseContext, data_loader: DataLoader) -> CaseContext:
        claimed_order_id = context.claimed_order_id
        order = data_loader.get_order(claimed_order_id)
        
        if order:
            context.flags.order_status = order.get("order_status", "")
        else:
            context.flags.order_status = ""
            
        context.affected_entities.order_ids = [claimed_order_id]
        
        items = data_loader.get_order_items(claimed_order_id)
        
        if not items:
            context.flags.has_items = False
            context.affected_entities.item_ids = []
            context.affected_entities.seller_ids = []
            context.product_context.product_ids = []
            context.product_context.category_names = []
            context.payment_reconciliation.item_total_brl = None
            context.payment_reconciliation.freight_total_brl = None
            context.payment_reconciliation.expected_total_brl = None
            context.flags.multi_item_order = False
            context.flags.multi_seller_order = False
            context.flags.multiple_categories = False
        else:
            context.flags.has_items = True
            
            # item_ids: all items
            item_ids = [f"{claimed_order_id}:{item['order_item_id']}" for item in items]
            context.affected_entities.item_ids = item_ids
            
            # seller_ids: unique seller_ids
            seller_ids = []
            for item in items:
                sid = item.get("seller_id")
                if sid and sid not in seller_ids:
                    seller_ids.append(sid)
            context.affected_entities.seller_ids = seller_ids
            
            # product_ids & category_names (unique)
            product_ids = []
            category_names = []
            for item in items:
                pid = item.get("product_id")
                if pid and pid not in product_ids:
                    product_ids.append(pid)
                    prod = data_loader.get_product(pid)
                    if prod and prod.get("product_category_name"):
                        cat_pt = prod["product_category_name"]
                        cat_en = data_loader.translate_category(cat_pt)
                        if cat_en and cat_en not in category_names:
                            category_names.append(cat_en)
                            
            context.product_context.product_ids = product_ids
            context.product_context.category_names = category_names
            
            # Financial calculations (round 2 decimals)
            item_total = sum(float(item["price"]) for item in items)
            freight_total = sum(float(item["freight_value"]) for item in items)
            
            item_total_brl = round(item_total, 2)
            freight_total_brl = round(freight_total, 2)
            expected_total_brl = round(item_total_brl + freight_total_brl, 2)
            
            context.payment_reconciliation.item_total_brl = item_total_brl
            context.payment_reconciliation.freight_total_brl = freight_total_brl
            context.payment_reconciliation.expected_total_brl = expected_total_brl
            
            # Flags
            context.flags.multi_item_order = len(items) >= 2
            context.flags.multi_seller_order = len(seller_ids) >= 2
            context.flags.multiple_categories = len(category_names) >= 2
            
        return context
