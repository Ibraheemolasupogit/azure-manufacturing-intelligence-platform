# Demand Series And Grain

The default forecast grain is `product_id` plus `distribution_region`. `ordered_quantity` is the target because it represents customer demand at order date. `fulfilled_quantity`, delivery dates, and final order status are excluded from predictors because they can encode future fulfilment outcomes.

Daily demand is built from `order_date`, grouped by the configured series keys, and summed. Missing series/date combinations are filled with zero demand and marked with `calendar_filled_flag=true`; this convention means no order row was observed for that synthetic order-book date.
