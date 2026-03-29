import csv
import random
from faker import Faker

# Inicjalizacja generatora
fake = Faker('en_US')

NUM_KLIENCI = 200_000
NUM_ZAMOWIENIA = 10_000_000
NUM_OPINIE = 1_000_000

MARKET_DATA = {
    'Electronics': ['Smartphone', 'Laptop', 'Tablet', 'Smartwatch', 'Headphones'],
    'Home': ['Coffee Maker', 'Vacuum', 'Desk Lamp', 'Sofa', 'Air Purifier'],
    'Fashion': ['T-Shirt', 'Jeans', 'Sneakers', 'Winter Jacket', 'Leather Belt'],
    'Sport': ['Yoga Mat', 'Dumbbells', 'Bicycle', 'Tent', 'Running Shoes'],
    'Beauty': ['Perfume', 'Face Cream', 'Hair Dryer', 'Lipstick', 'Mascara']
}

def generate_ecommerce_system():

    # 1. CATEGORIES
    cats = list(MARKET_DATA.keys())
    with open('data/categories.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name'])
        for i, name in enumerate(cats, 1):
            writer.writerow([i, name])

    # 2. SUPPLIERS
    suppliers_ids = list(range(1, 21))
    with open('data/suppliers.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'country', 'phone'])
        for i in suppliers_ids:
            writer.writerow([i, fake.company(), fake.country(), fake.phone_number()])

    # 3. PRODUCTS & 4. PRODUCT_DETAILS
    product_ids = []
    with open('data/products.csv', 'w', newline='', encoding='utf-8') as f_p, \
         open('data/product_details.csv', 'w', newline='', encoding='utf-8') as f_d:
        p_writer = csv.writer(f_p)
        p_writer.writerow(['id', 'category_id', 'supplier_id', 'name', 'price'])
        d_writer = csv.writer(f_d)
        d_writer.writerow(['id', 'product_id', 'specs'])
        pid = 1
        for cid, cname in enumerate(cats, 1):
            for item in MARKET_DATA[cname]:
                for brand in ['A-Tech', 'Premium', 'ValueMax', 'EcoLine']:
                    price = round(random.uniform(20.0, 3000.0), 2)
                    p_writer.writerow([pid, cid, random.choice(suppliers_ids), f"{brand} {item}", price])
                    d_writer.writerow([pid, pid, f"Color: {fake.color_name()}, Material: {fake.word()}, Warranty: 2 years"])
                    product_ids.append(pid)
                    pid += 1

    # 5. CUSTOMERS & 6. ADDRESSES 
    with open('data/customers.csv', 'w', newline='', encoding='utf-8') as f_c, \
         open('data/addresses.csv', 'w', newline='', encoding='utf-8') as f_a:
        c_writer = csv.writer(f_c)
        c_writer.writerow(['id', 'first_name', 'last_name', 'email', 'registration_date'])
        a_writer = csv.writer(f_a)
        a_writer.writerow(['id', 'customer_id', 'street', 'city', 'zip_code'])
        for cid in range(1, NUM_KLIENCI + 1):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = first_name + last_name + '@example.com'
            c_writer.writerow([cid, first_name, last_name, email, fake.date_between(start_date='-5y', end_date='-1y')])
            for _ in range(random.randint(1, 2)): 
                a_writer.writerow([cid, fake.street_address().replace(',', ''), fake.city(), fake.postcode()])

    # 7. COUPONS
    coupon_ids = list(range(1, 51))
    with open('data/coupons.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'code', 'discount_pct'])
        for i in coupon_ids:
            writer.writerow([i, f"SAVE{random.randint(10,50)}", random.randint(5, 25)])

    # 8. ORDERS & 9. ORDER_ITEMS
    with open('data/orders.csv', 'w', newline='', encoding='utf-8') as f_o, \
         open('data/order_items.csv', 'w', newline='', encoding='utf-8') as f_i:
        o_writer = csv.writer(f_o)
        o_writer.writerow(['id', 'customer_id', 'coupon_id', 'order_date', 'status', 'total_price'])
        i_writer = csv.writer(f_i)
        i_writer.writerow(['id', 'order_id', 'product_id', 'quantity', 'unit_price'])
        
        status_options = ['delivered', 'shipped', 'paid', 'cancelled']
        item_id = 1
        
        for oid in range(1, NUM_ZAMOWIENIA + 1):
            cid = random.randint(1, NUM_KLIENCI)
            coupon = random.choice(coupon_ids) if random.random() < 0.2 else "" 
            order_date = fake.date_this_year()
            status = random.choice(status_options)
            
            num_items = random.randint(1, 4)
            total_price = 0
            
            for _ in range(num_items):
                p_id = random.choice(product_ids)
                qty = random.randint(1, 3)
                u_price = round(random.uniform(20.0, 2500.0), 2)
                i_writer.writerow([item_id, oid, p_id, qty, u_price])
                total_price += (qty * u_price)
                item_id += 1
                
            o_writer.writerow([oid, cid, coupon, order_date, status, round(total_price, 2)])
            

    # 10. REVIEWS
    with open('data/reviews.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'product_id', 'customer_id', 'rating', 'comment'])
        for i in range(1, NUM_OPINIE + 1):
            writer.writerow([i, random.choice(product_ids), random.randint(1, NUM_KLIENCI), random.randint(1, 5), fake.sentence()])

    print("Done")

if __name__ == "__main__":
    generate_ecommerce_system()