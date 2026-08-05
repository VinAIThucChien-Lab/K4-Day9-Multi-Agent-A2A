import json
import os
from src.schemas import CaseContext
from src.data_loader import DataLoader
from src.agents.customer_agent import CustomerAgent
from src.agents.order_product_agent import OrderProductAgent

def test_step2():
    print("Initializing DataLoader...")
    dl = DataLoader()
    
    # Load sample case EC_001.json
    case_path = os.path.join("input", "input", "EC_001.json")
    if not os.path.exists(case_path):
        case_path = os.path.join("input", "EC_001.json")
        
    with open(case_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if "claimed_order_id" not in data:
        data["claimed_order_id"] = data.get("customer_request", {}).get("claimed_order_id", "")
    ctx = CaseContext(**data)
    print(f"Case ID: {ctx.case_id}, Claimed Order ID: {ctx.claimed_order_id}")
    
    # Step 2.1: CustomerAgent
    customer_agent = CustomerAgent()
    ctx = customer_agent.process(ctx, dl)
    print("\n--- CustomerAgent Result ---")
    print(f"Customer Context: {ctx.customer_context}")
    print(f"Repeat Customer Flag: {ctx.flags.repeat_customer}")
    
    # Step 2.2: OrderProductAgent
    order_product_agent = OrderProductAgent()
    ctx = order_product_agent.process(ctx, dl)
    print("\n--- OrderProductAgent Result ---")
    print(f"Order Status: {ctx.flags.order_status}")
    print(f"Has Items: {ctx.flags.has_items}")
    print(f"Affected Order IDs: {ctx.affected_entities.order_ids}")
    print(f"Affected Item IDs: {ctx.affected_entities.item_ids}")
    print(f"Affected Seller IDs: {ctx.affected_entities.seller_ids}")
    print(f"Product IDs: {ctx.product_context.product_ids}")
    print(f"Category Names: {ctx.product_context.category_names}")
    print(f"Item Total BRL: {ctx.payment_reconciliation.item_total_brl}")
    print(f"Freight Total BRL: {ctx.payment_reconciliation.freight_total_brl}")
    print(f"Expected Total BRL: {ctx.payment_reconciliation.expected_total_brl}")
    print(f"Multi-item: {ctx.flags.multi_item_order}")
    print(f"Multi-seller: {ctx.flags.multi_seller_order}")
    print(f"Multi-categories: {ctx.flags.multiple_categories}")

if __name__ == "__main__":
    test_step2()
