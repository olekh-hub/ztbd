# Redis Secondary Indexes

Redis has no automatic secondary indexes, so supported benchmark scenarios need explicit keys maintained by ingestion or scenario setup.

Recommended keys:

- `email:{email} -> customer_id` for R1 and U1 point lookup by email.
- `customer:{id}` hash for customer attributes.
- `customer:{id}:addresses` JSON string for embedded addresses.
- `product:{id}` hash for product attributes.
- `product:{product_id}:reviews` list of review ids.
- `review:{id}` hash for review attributes.
- `order:{id}` JSON string for denormalized orders.
- `product_rating:{product_id}:{rating}` set of review ids for D3-style selective deletes.

Redis scenarios marked unsupported in `scenarios/scenarios.md` should be skipped rather than forced into non-equivalent workloads.
