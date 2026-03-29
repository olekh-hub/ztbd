import pandas as pd
import json
import os
from pymongo import MongoClient
import redis

# connecting do mongo db
mongo_client = MongoClient('mongodb://localhost:27017')
mongo_db = mongo_client['ecommerce_db']

# clearing before import
mongo_db.customers.drop()
mongo_db.products.drop()
mongo_db.orders.drop()
mongo_db.reviews.drop()

# redis connection
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
r.flushdb()

# csv files import
addresses = pd.read_csv('data/addresses.csv')
categories = pd.read_csv('data/categories.csv')
coupons = pd.read_csv('data/coupons.csv')
customers = pd.read_csv('data/customers.csv')
order_items = pd.read_csv('data/order_items.csv')
# orders = pd.read_csv('data/orders.csv')
product_details = pd.read_csv('data/product_details.csv')
products = pd.read_csv('data/products.csv')
reviews = pd.read_csv('data/reviews.csv')
suppliers = pd.read_csv('data/suppliers.csv')

# customers transformation
print('processing customers and their addresses')
# create a list of addresses for a certain customer
addresses_grouped = addresses.groupby('customer_id').apply(lambda x: x.drop('customer_id', axis=1).to_dict('records')).to_dict()

mongo_customers = []
# iterrate through each client
for _, row in customers.iterrows(): 
    cust_dict = row.to_dict() # row -> dict 
    cust_dict['_id'] = int(cust_dict.pop('id')) # mongo db's requirement
    cust_dict['addresses'] = addresses_grouped.get(cust_dict['_id'], []) # create a new field addresses, get - 
    mongo_customers.append(cust_dict)

if mongo_customers:
    mongo_db.customers.insert_many(mongo_customers)

for cust in mongo_customers:
    redis_hash = {
        'first_name': str(cust['first_name']),
        'last_name': str(cust['last_name']),
        'email': str(cust['email']),
        'registration_date': str(cust['registration_date'])
    }
    r.hset(f'customer:{cust["_id"]}', mapping=redis_hash)
    r.set(f'customer:{cust["_id"]}:addresses', json.dumps(cust['addresses']))

# products transformation
print(f'processing products, categories and suppliers')

# create dicts and set indexes for a faster finding
cat_dict = categories.set_index('id').to_dict('index')
sup_dict = suppliers.set_index('id').to_dict('index')
det_dict = product_details.set_index('id').to_dict('index')

mongo_products = []
for _, row in products.iterrows():
    prod_dict = row.to_dict() # it is a new row 
    prod_dict['_id'] = int(prod_dict.pop('id')) # product id 
    prod_dict['category'] = cat_dict.get(prod_dict['category_id'], {}) # get category which id is equal to 
    prod_dict['supplier'] = sup_dict.get(prod_dict['supplier_id'], {})
    prod_dict['specs'] = det_dict.get(prod_dict['_id'], {}).get('specs', '')

    prod_dict.pop('category_id')
    prod_dict.pop('supplier_id')

    mongo_products.append(prod_dict)

if mongo_products:
    mongo_db.products.insert_many(mongo_products)

for prod in mongo_products:
    redis_hash = {
        'name': str(prod['name']),
        'price': str(prod['price']),
        'category_name': str(prod.get('category', {}).get('name', '')),
        'supplier_name': str(prod.get('supplier', {}).get('name', '')),
        'specs': str(prod['specs'])
    }
    r.hset(f'product:{prod["_id"]}', mapping=redis_hash)   

# reviews transform
print(f'processing reviews') 
mongo_reviews = []
for _, row in reviews.iterrows():
    review_dict = row.to_dict()
    review_dict['_id'] = int(review_dict.pop('id'))

    mongo_reviews.append(review_dict)

if mongo_reviews:
    mongo_db.reviews.insert_many(mongo_reviews)

for rev in mongo_reviews:
    r.hset(f"review:{rev['_id']}", mapping={
        'product_id': str(rev['product_id']),
        'customer_id': str(rev['customer_id']),
        'rating': str(rev['rating']),
        'comment': str(rev['comment'])
    })
    
    r.lpush(f"product:{rev['product_id']}:reviews", rev['_id'])

# orders transform
print(f'processing orders, items and coupons')
coup_dict = coupons.set_index('id').to_dict('index')

print('start grouping')
# items_grouped = order_items.groupby('order_id').apply(lambda x: x.drop('order_id', axis=1).to_dict('records')).to_dict()
from collections import defaultdict
items_dict = defaultdict(list)
for _, row in order_items.iterrows():
    d = row.to_dict()
    oid = int(d.pop('order_id'))
    items_dict[oid].append(d)

import gc
del order_items
gc.collect()
print('grouping ended')

batch_size = 5000
reader = pd.read_csv('data/orders.csv', chunksize=batch_size)

for chunk in reader:
    mongo_orders = []
    for _, row in chunk.iterrows():
        order_dict = row.to_dict()
        order_dict['_id'] = int(order_dict.pop('id'))
        order_dict['items'] = items_dict.get(order_dict['_id'], [])

        coupon_id = order_dict.pop('coupon_id', None)
        if not pd.isna(coupon_id):
            order_dict['coupon'] = coup_dict.get(coupon_id, {})
        
        mongo_orders.append(order_dict)

    if mongo_orders:
        mongo_db.orders.insert_many(mongo_orders)

    for order in mongo_orders:
        r.set(f'order:{order["_id"]}', json.dumps(order, default=str))

    print(f'imported {batch_size} orders')


