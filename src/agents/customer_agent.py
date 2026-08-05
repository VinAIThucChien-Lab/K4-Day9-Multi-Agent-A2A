from src.schemas import CaseContext, CustomerContext
from src.data_loader import DataLoader

class CustomerAgent:
    def process(self, context: CaseContext, data_loader: DataLoader) -> CaseContext:
        claimed_order_id = context.claimed_order_id
        customer_id = data_loader.get_customer_id_by_order(claimed_order_id)
        
        if not customer_id:
            context.customer_context = CustomerContext(
                customer_unique_id="",
                related_order_ids=[]
            )
            context.flags.repeat_customer = False
            return context

        customer_unique_id = data_loader.get_customer_unique_id(customer_id)
        related_orders = data_loader.get_customer_history(customer_unique_id, exclude_order_id=claimed_order_id)
        
        # Max 5 related order IDs
        related_order_ids = related_orders[:5]
        
        context.customer_context = CustomerContext(
            customer_unique_id=customer_unique_id,
            related_order_ids=related_order_ids
        )
        context.flags.repeat_customer = len(related_order_ids) > 0
        return context
